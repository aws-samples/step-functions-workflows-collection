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
sfn = boto3.client('stepfunctions', config=RETRY_CONFIG)

JOBS_TABLE_NAME = os.environ['JOBS_TABLE_NAME']


def handler(event, context):
    """
    Triggered by EventBridge on terminal batch job states.
    Looks up task token and resumes the state machine.
    """
    try:
        logger.info(json.dumps({'event': 'resume_invoked', 'input': event}))

        # Extract batch job details from EventBridge event
        detail = event['detail']
        bedrock_job_arn = detail['batchJobArn']
        status = detail['status']

        logger.info(json.dumps({
            'event': 'batch_job_terminal_state',
            'job_arn': bedrock_job_arn,
            'status': status
        }))

        # Query DynamoDB to find the job by BedrockJobArn using GSI
        response = dynamodb.query(
            TableName=JOBS_TABLE_NAME,
            IndexName='BedrockJobArnIndex',
            KeyConditionExpression='BedrockJobArn = :arn',
            ExpressionAttributeValues={
                ':arn': {'S': bedrock_job_arn}
            }
        )

        if not response['Items']:
            logger.warning(json.dumps({
                'event': 'job_not_found',
                'bedrock_job_arn': bedrock_job_arn
            }))
            return {'statusCode': 404, 'message': 'Job not found'}

        item = response['Items'][0]
        task_token = item['TaskToken']['S']
        job_id = item['JobId']['S']

        # Update job status in DynamoDB
        dynamodb.update_item(
            TableName=JOBS_TABLE_NAME,
            Key={'JobId': {'S': job_id}},
            UpdateExpression='SET #status = :status, LastUpdated = :updated',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':status': {'S': status},
                ':updated': {'S': datetime.now(timezone.utc).isoformat()}
            }
        )

        # Resume state machine — CheckOutcome routes based on status
        output = {'status': status, 'bedrockJobArn': bedrock_job_arn}
        sfn.send_task_success(
            taskToken=task_token,
            output=json.dumps(output)
        )
        logger.info(json.dumps({
            'event': 'task_success_sent',
            'job_id': job_id,
            'status': status
        }))

        return {
            'statusCode': 200,
            'body': json.dumps({'jobId': job_id, 'status': status})
        }

    except Exception as e:
        logger.error(json.dumps({
            'event': 'resume_error',
            'error': str(e),
            'error_type': type(e).__name__
        }))
        raise
