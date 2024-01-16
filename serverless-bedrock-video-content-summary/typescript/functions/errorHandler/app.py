import json
import boto3
import os

topic_arn = os.environ["TOPIC_ARN"]
sns = boto3.client("sns")
ddb = boto3.resource("dynamodb")
table = ddb.Table(os.environ["DDB_TABLE_NAME"])
message={}

def lambda_handler(event, context):
    print(event)
    source = event["source"]
    detail_type = event["detail-type"]
    id = event['id']

    # error handling for media convert 
    if source == "aws.mediaconvert" and detail_type == "MediaConvert Job State Change": 
        print("mediaconvert Failure")
        message={
            "failed_resources": event["resources"],
            "error_message": event["detail"]["errorMessage"],
            "job_id": event["detail"]["jobId"]
        }

    # error handling for media package 
    if source == "aws.mediapackage" and detail_type == "MediaPackage Input Notification":
        print("mediapackage assect creation failure")
        message={
            "failed_resources": event["resources"],
            "error_message": event["detail"]["message"]
        }

    # error handling for step functions  
    if source == "aws.states" and detail_type == "Step Functions Execution Status Change":
        print("stepfunction failure")
        message={
            "execution_arn" : event["detail"]["executionArn"],
            "failed_resources": event["detail"]["stateMachineArn"],
            "error_message": event["detail"]["cause"]
        }
    # Send notification and log to ddb 
    message["id"] = id
    try:
        sns_pub(json.dumps(message))
        table.put_item(
            Item=message
        )
    except Exception as error:
        print(error)
        raise

def sns_pub(message: str()):
    sns_response = sns.publish(
        TopicArn = topic_arn,
        Message = message,
    )

