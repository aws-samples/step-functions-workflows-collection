import boto3
import os
import json

client = boto3.client('stepfunctions')
stepfunctions_arn = os.environ.get('STEP_FUNCTIONS_ARN')

def handler(event, context):
    connectionId = event['requestContext']['connectionId']

    client.start_execution(
        stateMachineArn=stepfunctions_arn,
        input=json.dumps({'ConnectionId': connectionId})
    )
            
    return {
        'statusCode': 200
    }
