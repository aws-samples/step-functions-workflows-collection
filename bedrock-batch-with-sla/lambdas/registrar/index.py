import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
import boto3

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.boto_config import RETRY_CONFIG

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.client('dynamodb', config=RETRY_CONFIG)
sfn = boto3.client('stepfunctions', config=RETRY_CONFIG)

JOBS_TABLE_NAME = os.environ['JOBS_TABLE_NAME']
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']
OUTPUT_BUCKET_NAME = os.environ['OUTPUT_BUCKET_NAME']


def handler(event, context):
    """
    Triggered by S3 ObjectCreated event on input bucket.
    Creates DynamoDB job record and starts Step Functions execution.
    """
    try:
        logger.info(json.dumps({'event': 'registrar_invoked', 'input': event}))

        # Extract S3 event details
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        s3_input_uri = f"s3://{bucket}/{key}"
        job_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        # Create DynamoDB record
        dynamodb.put_item(
            TableName=JOBS_TABLE_NAME,
            Item={
                'JobId': {'S': job_id},
                'Status': {'S': 'Pending'},
                'CreatedAt': {'S': created_at},
                'S3InputLocation': {'S': s3_input_uri},
                'S3OutputLocation': {'S': f"s3://{OUTPUT_BUCKET_NAME}/batch-output/{job_id}/"},
                'ModelId': {'S': os.environ['MODEL_ID']},
                'LastUpdated': {'S': created_at},
            }
        )

        logger.info(json.dumps({
            'event': 'job_registered',
            'job_id': job_id,
            'input_uri': s3_input_uri
        }))

        # Start Step Functions execution
        execution_input = {
            'jobId': job_id,
            'inputUri': s3_input_uri,
            'outputUri': f"s3://{OUTPUT_BUCKET_NAME}/batch-output/{job_id}/",
        }

        response = sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"batch-job-{job_id}",
            input=json.dumps(execution_input)
        )

        logger.info(json.dumps({
            'event': 'execution_started',
            'job_id': job_id,
            'execution_arn': response['executionArn']
        }))

        return {
            'statusCode': 200,
            'body': json.dumps({
                'jobId': job_id,
                'executionArn': response['executionArn']
            })
        }

    except Exception as e:
        logger.error(json.dumps({
            'event': 'registrar_error',
            'error': str(e),
            'error_type': type(e).__name__
        }))
        raise
