# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import boto3

'''
Dummy handler for UML impl in Step Functions.
'''

def lambda_handler(event, context):
    # log the event. event has SM tracing in it.
    # this just goes to CW logs. good enough tracing for this blog post
    print("Logging UML trace event")
    print(event)
        
    return event
