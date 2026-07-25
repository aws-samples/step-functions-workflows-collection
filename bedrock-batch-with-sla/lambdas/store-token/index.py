import json
import logging
import os
import sys
from datetime import datetime, timezone
import boto3

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.boto_config import RETRY_CONFIG

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.client('dynamodb', config=RETRY_CONFIG)

JOBS_TABLE_NAME = os.environ['JOBS_TABLE_NAME']


def handler(event, context):
    """
    Invoked by Step Functions with waitForTaskToken.
    Stores the task token and job info in DynamoDB for later resume.
    """
    try:
        logger.info(json.dumps({'event': 'store_token_invoked', 'input': event}))

        job_id = event['jobId']
        bedrock_job_arn = event['bedrockJobArn']
        task_token = event['taskToken']
        model_id = os.environ['MODEL_ID']

        # Update DynamoDB with task token and batch job details
        dynamodb.update_item(
            TableName=JOBS_TABLE_NAME,
            Key={'JobId': {'S': job_id}},
            UpdateExpression='SET TaskToken = :token, BedrockJobArn = :arn, ModelId = :model, #status = :status, LastUpdated = :updated',
            ExpressionAttributeNames={
                '#status': 'Status'
            },
            ExpressionAttributeValues={
                ':token': {'S': task_token},
                ':arn': {'S': bedrock_job_arn},
                ':model': {'S': model_id},
                ':status': {'S': 'InProgress'},
                ':updated': {'S': datetime.now(timezone.utc).isoformat()}
            }
        )

        logger.info(json.dumps({
            'event': 'token_stored',
            'job_id': job_id,
            'bedrock_job_arn': bedrock_job_arn
        }))

        # Return success (does not resume the state machine)
        return {
            'statusCode': 200,
            'message': 'Task token stored successfully'
        }

    except Exception as e:
        logger.error(json.dumps({
            'event': 'store_token_error',
            'error': str(e),
            'error_type': type(e).__name__
        }))
        raise
