import json
import logging
import os
import sys
from datetime import datetime, timezone
import boto3

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.boto_config import RETRY_CONFIG, EXTENDED_TIMEOUT_CONFIG

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.client('dynamodb', config=RETRY_CONFIG)
bedrock = boto3.client('bedrock', config=EXTENDED_TIMEOUT_CONFIG)  # Longer timeout for Bedrock API
sfn = boto3.client('stepfunctions', config=RETRY_CONFIG)

JOBS_TABLE_NAME = os.environ['JOBS_TABLE_NAME']
MODEL_ID = os.environ['MODEL_ID']


def handler(event, context):
    """
    Triggered by SNS from CloudWatch alarm for stuck/slow jobs.
    Resolves which job is affected and triggers fallback.
    """
    try:
        logger.info(json.dumps({'event': 'trigger_invoked', 'input': event}))

        # Parse SNS message from CloudWatch alarm
        message = json.loads(event['Records'][0]['Sns']['Message'])
        alarm_name = message.get('AlarmName', 'unknown')

        logger.info(json.dumps({
            'event': 'alarm_triggered',
            'alarm_name': alarm_name
        }))

        # Query DynamoDB for InProgress jobs on this ModelId
        response = dynamodb.query(
            TableName=JOBS_TABLE_NAME,
            IndexName='StatusIndex',
            KeyConditionExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':status': {'S': 'InProgress'}
            }
        )

        if not response['Items']:
            logger.warning(json.dumps({
                'event': 'no_active_jobs_found',
                'model_id': MODEL_ID
            }))
            return {'statusCode': 200, 'message': 'No active jobs to trigger'}

        # Check each job to confirm it's stuck
        for item in response['Items']:
            job_id = item['JobId']['S']
            bedrock_job_arn = item['BedrockJobArn']['S']
            task_token = item['TaskToken']['S']

            # Get job details from Bedrock
            try:
                job_details = bedrock.get_model_invocation_job(jobIdentifier=bedrock_job_arn)

                job_status = job_details['status']
                pending = job_details.get('inputDataConfig', {}).get('recordCount', 0)
                processed = job_details.get('outputDataConfig', {}).get('recordCount', 0)

                logger.info(json.dumps({
                    'event': 'job_checked',
                    'job_id': job_id,
                    'status': job_status,
                    'pending': pending,
                    'processed': processed
                }))

                # If job is stuck (Scheduled, Validating, or InProgress)
                # For early states (Validating), we can't check pending > processed yet
                # so we trigger fallback for any job in these states when alarm fires
                if job_status in ['Scheduled', 'Validating', 'InProgress']:
                    logger.info(json.dumps({
                        'event': 'triggering_fallback',
                        'job_id': job_id,
                        'reason': 'stuck_job'
                    }))

                    # Resume state machine with fallback signal
                    output = {
                        'status': 'FallbackRequested',
                        'bedrockJobArn': bedrock_job_arn,
                        'reason': 'stuck_or_slow'
                    }

                    sfn.send_task_success(
                        taskToken=task_token,
                        output=json.dumps(output)
                    )

                    # Update DynamoDB
                    dynamodb.update_item(
                        TableName=JOBS_TABLE_NAME,
                        Key={'JobId': {'S': job_id}},
                        UpdateExpression='SET LastUpdated = :updated',
                        ExpressionAttributeValues={
                            ':updated': {'S': datetime.now(timezone.utc).isoformat()}
                        }
                    )

                    return {
                        'statusCode': 200,
                        'body': json.dumps({'jobId': job_id, 'action': 'fallback_triggered'})
                    }

            except Exception as e:
                logger.error(json.dumps({
                    'event': 'job_check_error',
                    'job_id': job_id,
                    'error': str(e)
                }))
                continue

        logger.info(json.dumps({'event': 'no_stuck_jobs_found'}))
        return {'statusCode': 200, 'message': 'No stuck jobs found'}

    except Exception as e:
        logger.error(json.dumps({
            'event': 'trigger_error',
            'error': str(e),
            'error_type': type(e).__name__
        }))
        raise
