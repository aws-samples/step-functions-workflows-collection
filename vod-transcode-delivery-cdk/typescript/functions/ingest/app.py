import json
import boto3
import os

sfn = boto3.client('stepfunctions')

def lambda_handler(event, context):
    try: 
        source_s3_key = event['Records'][0]['s3']['object']['key']
        source_s3_bucket = event['Records'][0]['s3']['bucket']['name']
        source_s3 = 's3://' + source_s3_bucket + '/' + source_s3_key
        # the error message is included in the final report.
        sfn_input={
                "sourceS3": source_s3,
                "sourceS3Bucket": source_s3_bucket,
                "sourceS3Key": source_s3_key
                }
        
    except Exception as error:
        print("excpetion in getting the s3 ",error)
        raise

    try:
        sfn.start_execution(
            stateMachineArn=os.environ['SFN_ARN'],
            input=str(sfn_input).replace("'", "\"")
        )
        # print(response)
        return sfn_input
    except Exception as error:
        print("exception when starting the sfn", error)
        raise
