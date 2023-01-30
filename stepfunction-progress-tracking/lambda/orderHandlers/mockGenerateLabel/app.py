import boto3
import os
import time
import json

client = boto3.client('lambda')
lambda_func_name = os.environ.get('REPORT_PROGRESS_LAMBDA')


def handler(event, context):
    print(event['ConnectionId'])

    # Do something here

    # Wait for 3 seconds
    time.sleep(3)

    print("Label successfully generated.");

    return {
        'statusCode': 200,
        'ConnectionId': event['ConnectionId']
    }
