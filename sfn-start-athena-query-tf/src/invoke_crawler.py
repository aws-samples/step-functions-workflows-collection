import json
import boto3
import time
import os

ATHENA_CRAWLER = os.environ['ATHENA_CRAWLER']

MAX_RETRY = 20

def lambda_handler(event, context):
    client = boto3.client('glue')
    response = client.start_crawler(
        Name=ATHENA_CRAWLER
    )
    retry_count = 1
    while retry_count < MAX_RETRY:
        time.sleep(30)
        crawler_status = client.get_crawler(
            Name=ATHENA_CRAWLER
        )
        crawler_run_status = crawler_status['Crawler']['State']
        if crawler_run_status == 'READY':
            break
        retry_count += 1
    return {
        'statusCode': 200,
        'body': json.dumps('Crawler completes')
    }
