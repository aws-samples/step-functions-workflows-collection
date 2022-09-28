# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import boto3
'''
Dummy handler for UML impl in Step Functions.
'''
def lambda_handler(event, context):
              
    print("Logging application event")
    print(event)
            
    sfn = boto3.client('stepfunctions')
    task_token = event['taskToken']
    event['taskToken'] = "" # clear it because it's no longer needed
    app_event = {
                'appEvent': event
    }
    sfn.send_task_success(
        taskToken=task_token,
        output=json.dumps(app_event))
            
            
    return event
