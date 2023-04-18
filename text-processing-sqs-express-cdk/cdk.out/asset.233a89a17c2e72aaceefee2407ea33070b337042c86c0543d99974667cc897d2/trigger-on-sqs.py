import boto3
import os
def lambda_handler(event, context):
    message_body = event['Records'][0]['body']
    client = boto3.client('stepfunctions')
    response = client.start_execution(
        stateMachineArn= os.environ['STATE_MACHINE_ARN'],
        input=message_body
    )