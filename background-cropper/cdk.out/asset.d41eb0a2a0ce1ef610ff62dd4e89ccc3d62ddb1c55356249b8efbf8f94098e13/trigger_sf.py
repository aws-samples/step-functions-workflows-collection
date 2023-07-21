import json
import boto3
import os
import pprint

sfn_arn = os.environ['STEP_FUNCTION_ARN'] 
def lambda_handler(event, context):
    #trigger step functions from S3 landing event, passing along S3 name and file name
 
    bucket = event['Records'][0]['s3']['bucket']['name']
    fname = event['Records'][0]['s3']['object']['key']
    input = {
            'Bucket': bucket,
            'FileName': fname
    }
        
    step_function = boto3.client('stepfunctions')
    response = step_function.start_execution(
        #replace with proper stateMachine
        stateMachineArn=sfn_arn,
        input = json.dumps(input,indent=4)
    )
    