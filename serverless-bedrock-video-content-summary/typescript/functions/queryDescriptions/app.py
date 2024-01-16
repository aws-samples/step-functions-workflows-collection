import boto3
import json
import os
table_name = os.environ["TABLE_NAME"]
ddb = boto3.resource("dynamodb")
table = ddb.Table(table_name)

def lambda_handler(event, context):
    video_id = event["pathParameters"]["videoId"]
    try:
        response = table.get_item(Key={
            "video_id": video_id
        })

        item = response["Item"]
        return {
            "statusCode": 200,
            "body": json.dumps({"item": item}),
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Content-Type": "application/json",
            }
        }
    
    except Exception as error: 
        return {
            "statusCode": 500,
            "body": str(error),
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Content-Type": "application/json",
            }
        }