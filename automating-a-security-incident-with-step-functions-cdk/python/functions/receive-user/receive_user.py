import boto3
import json
import logging

client = boto3.client("stepfunctions")
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger()


def handler(event, context):
    logger.setLevel(logging.INFO)
    next_action = "deny"
    if event["requestContext"]["resourcePath"] == "/allow":
        next_action = "allow"
    task_token = event["queryStringParameters"]["token"]
    task_token_clean = task_token.replace(" ", "")
    logger.info(f"token received: {task_token_clean}")

    output_to_send = {"action": next_action}
    client.send_task_success(
        output=json.dumps(output_to_send), taskToken=task_token_clean
    )
    return {
        "statusCode": 200,
        "body": json.dumps(output_to_send),
        "headers": {
            "Content-Type": "application/json",
        },
    }
