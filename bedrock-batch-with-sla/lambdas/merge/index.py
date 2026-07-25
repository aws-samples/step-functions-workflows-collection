import json
import logging
import os
import sys
import boto3

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.boto_config import RETRY_CONFIG
from common.s3_utils import parse_s3_uri, read_json_from_s3, read_jsonl_from_s3, write_jsonl_to_s3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3', config=RETRY_CONFIG)

OUTPUT_BUCKET_NAME = os.environ['OUTPUT_BUCKET_NAME']


def handler(event, context):
    """
    Merges batch-partial output + on-demand results into unified output.
    Ensures one result per recordId.
    """
    try:
        logger.info(json.dumps({'event': 'merge_invoked', 'input': event}))

        job_id = event['jobId']
        output_uri = event['outputUri']

        # Parse S3 URI
        output_bucket, output_prefix = parse_s3_uri(output_uri)

        # Read batch output (if any)
        batch_results = {}
        try:
            output_prefix_clean = output_prefix.rstrip('/')
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=output_bucket, Prefix=output_prefix_clean):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if key.endswith('.jsonl.out'):
                        records = read_jsonl_from_s3(s3, output_bucket, key)
                        for rec in records:
                            if 'recordId' in rec:
                                batch_results[rec['recordId']] = rec

            logger.info(json.dumps({
                'event': 'batch_results_loaded',
                'count': len(batch_results)
            }))
        except Exception as e:
            logger.warning(json.dumps({
                'event': 'batch_results_not_found',
                'error': str(e)
            }))

        # Read on-demand results (from Distributed Map ResultWriter)
        # ResultWriter writes child execution envelopes: [{ExecutionArn, Input, Output, Status}, ...]
        # Output is a JSON string containing the state machine result for that item.
        ondemand_results = {}
        try:
            ondemand_prefix = f"ondemand-results/{job_id}/"
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=OUTPUT_BUCKET_NAME, Prefix=ondemand_prefix):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if not key.endswith('.json') or key.endswith('manifest.json'):
                        continue
                    executions = read_json_from_s3(s3, OUTPUT_BUCKET_NAME, key)
                    if not isinstance(executions, list):
                        executions = [executions]
                    for execution in executions:
                        if execution.get('Status') != 'SUCCEEDED':
                            continue
                        output_str = execution.get('Output')
                        if not output_str:
                            continue
                        result = json.loads(output_str)
                        # result contains modelOutput.recordId and modelOutput.body
                        model_output = result.get('modelOutput', {})
                        record_id = model_output.get('recordId')
                        if record_id:
                            ondemand_results[record_id] = {
                                'recordId': record_id,
                                'modelOutput': model_output.get('body', {})
                            }

            logger.info(json.dumps({
                'event': 'ondemand_results_loaded',
                'count': len(ondemand_results)
            }))
        except Exception as e:
            logger.warning(json.dumps({
                'event': 'ondemand_results_not_found',
                'error': str(e)
            }))

        # Merge results (on-demand takes precedence for duplicates)
        merged_results = {**batch_results, **ondemand_results}

        logger.info(json.dumps({
            'event': 'merge_complete',
            'batch_count': len(batch_results),
            'ondemand_count': len(ondemand_results),
            'merged_count': len(merged_results)
        }))

        # Write merged output (always write so downstream consumers can rely on the key existing)
        merged_key = f"merged-output/{job_id}/results.jsonl"
        write_jsonl_to_s3(s3, OUTPUT_BUCKET_NAME, merged_key, list(merged_results.values()))

        return {
            'statusCode': 200,
            'mergedKey': merged_key,
            'totalRecords': len(merged_results),
            'batchRecords': len(batch_results),
            'ondemandRecords': len(ondemand_results)
        }

    except Exception as e:
        logger.error(json.dumps({
            'event': 'merge_error',
            'error': str(e),
            'error_type': type(e).__name__
        }))
        raise


