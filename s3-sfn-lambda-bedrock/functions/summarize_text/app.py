import json
import boto3
import os
from urllib.parse import unquote_plus
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
s3 = boto3.client("s3")

def getSummaryFromText(content):
    model_id = os.environ['Model']
    bedrock_client = boto3.client("bedrock-runtime")

    system_prompt = os.environ['BedrockPrompt']
    max_tokens = 300

    user_message = {"role": "user", "content": content}
    messages = [user_message]

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": messages
    })

    response = bedrock_client.invoke_model(body=body, modelId=model_id)
    response_body = json.loads(response.get('body').read())

    summary_text = response_body['content'][0]['text']

    return summary_text

def readFile(bucket, key):
    s3_client = boto3.client("s3")
    fileObj = s3_client.get_object(Bucket=bucket, Key=key)
    file_content = fileObj["Body"].read().decode("utf-8")
    return file_content

def lambda_handler(event, context):
    txt_response = ""

    if event:
        print("event", event)
        
        # Get the staged key and bucket name from the Step Functions event
        source_key = event["SourceKey"]
        
        # Check if the 'detail' key exists in the event
        bucketname = event["Bucket"]
        
        file_content = readFile(bucketname, source_key)
        print(file_content)

        txt_response = getSummaryFromText(file_content)
        print("Response:")
        print(txt_response)

        # Write output file to S3 bucket
        output_data = {
            "original_content": file_content,
            "summary": txt_response,
            "model": os.environ['Model'],
            "datetime": str(datetime.now())
        }

        output_key = os.environ['NextPrefix'] + f"{source_key.split('/')[-1]}.json"
        s3.put_object(
            Body=json.dumps(output_data),
            Bucket=bucketname,
            Key=output_key
        )

    return {"statusCode": 200, "body": "File summary generated and uploaded to S3"}
