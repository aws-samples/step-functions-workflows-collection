"""
    MIT No Attribution

    Copyright 2022 Amazon Web Services

    Permission is hereby granted, free of charge, to any person obtaining a copy of this
    software and associated documentation files (the "Software"), to deal in the Software
    without restriction, including without limitation the rights to use, copy, modify,
    merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
    INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
    PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
    OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
    SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
import boto3
import json
import os
from urllib.parse import quote


def lambda_handler(event, context):
    task_token = quote(event['taskToken'], safe='')
    execution_id = event['execution']

    print(f"Sending approval email for execution: {execution_id}")
    print(f"Task token (first 50 chars): {event['taskToken'][:50]}...")

    api_endpoint = os.environ['API_ENDPOINT']
    approve_url = f"{api_endpoint}?taskToken={task_token}&decision=approve"
    reject_url = f"{api_endpoint}?taskToken={task_token}&decision=reject"

    message_data = {
        'default': 'Workflow Approval Required',
        'email': (
            f"Workflow Approval Required\n"
            f"{'=' * 40}\n\n"
            f"A new approval is required for workflow execution:\n"
            f"{execution_id}\n\n"
            f"To APPROVE, click the link below:\n"
            f"{approve_url}\n\n"
            f"To REJECT, click the link below:\n"
            f"{reject_url}\n"
        )
    }

    sns = boto3.client('sns')
    sns.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'],
        Subject='Step Functions Workflow - Approval Required',
        Message=json.dumps(message_data),
        MessageStructure='json'
    )

    return {
        'statusCode': 200,
        'body': 'Approval notification sent successfully'
    }
