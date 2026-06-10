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
from urllib.parse import unquote


def lambda_handler(event, context):
    query_params = event.get('queryStringParameters', {})
    task_token = unquote(query_params.get('taskToken', ''))
    decision = query_params.get('decision')

    print(f"Received request - decision: {decision}, taskToken (first 50 chars): {task_token[:50]}...")

    sfn = boto3.client('stepfunctions')

    try:
        if decision == 'approve':
            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps({'result': True})
            )
            message = 'Workflow approved successfully!'
        else:
            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps({'result': False})
            )
            message = 'Workflow rejected.'

        print(f"Successfully processed decision: {decision}")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html'},
            'body': f'<html><body><h2>{message}</h2></body></html>'
        }
    except Exception as e:
        print(f"Error processing decision '{decision}': {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/html'},
            'body': f'<html><body><h2>Error processing request</h2><p>{str(e)}</p></body></html>'
        }
