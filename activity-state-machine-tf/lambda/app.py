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
import json
import boto3
import os

client = boto3.client('stepfunctions')

def lambda_handler(event, context):
    
    # Get the activity ARN from the Environment Variables
    activity_Arn = os.environ.get('ACTIVITY')
    
    #Poll Step Functions by using GetActivityTask, and sending the ARN for the related activity
    activity_tasktoken = client.get_activity_task(activityArn=activity_Arn,workerName='LambdaWorker')

    output_json = {"Result": "value"}

    #After the activity worker completes its work, provide a report of its success or failure 
    send_task_success_response = client.send_task_success(taskToken=activity_tasktoken['taskToken'], output= json.dumps(output_json))
    
    print(send_task_success_response)

    return {
        'statusCode': 200,
        'body': json.dumps('Worker implementaion successfully completed!')
    }


