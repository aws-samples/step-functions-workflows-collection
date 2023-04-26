import os
import boto3
import urllib.parse
import logging

client = boto3.client("sns")
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger()


def handler(event, context):
    logger.setLevel(logging.INFO)
    topic_arn = os.environ["TOPIC_ARN"]
    allow_endpoint = os.environ["API_ALLOW_ENDPOINT"]
    deny_endpoint = os.environ["API_DENY_ENDPOINT"]

    query_params = {"token": event["token"]}
    query_string = urllib.parse.urlencode(query_params)
    logger.info(f"Encoded query string: {query_string}")

    client.publish(
        TopicArn=topic_arn,
        Message=f"A restricted policy change has been detected. \nTo approve: \n{allow_endpoint}?{query_string}\n Or \nTo deny: \n{deny_endpoint}?{query_string}",
    )
    return event
