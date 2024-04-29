import base64
import json
import os
import boto3
import logging

logger = logging.getLogger(__name__)

session = boto3.Session()
client = session.client(service_name="bedrock-runtime", region_name="us-east-1")
s3_client = boto3.client("s3")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET")


def encoded_image(bucket, key, size):
    image_bytes = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()
    return base64.b64encode(image_bytes).decode("utf-8")


def handler(event, context):
    logger.info(event)

    for record in event.get("Items"):
        bucket = record.get("Bucket")
        key = record.get("Data").get("Key")
        size = record.get("Data").get("Size")

        data = encoded_image(bucket, key, size)
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": data,
                                },
                            },
                            {
                                "type": "text",
                                "text": "Generate a HTML alternate text complete code describing what is in this image. The description should be concise for vision impaired readers.",
                            },
                        ],
                    }
                ],
            }
        )

        response = client.invoke_model(modelId=CLAUDE_MODEL, body=body)
        response_body = json.loads(response.get("body").read())
        print(response_body)
        logger.info(response_body)
        text = response_body.get("content")[0].get("text")
        payload = {
            "bucket": OUTPUT_BUCKET,
            "key": f"{key}.html",
            "text": text,
        }

        return payload
