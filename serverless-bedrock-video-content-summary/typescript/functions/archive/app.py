import boto3
import os
import json

s3 = boto3.client('s3')
archive_bucket = os.environ['ARCHIVE_BUCKET']
def lambda_handler(event, context):
    print(f'Event: {json.dumps(event)}')
    source_key = event['source_s3_key']
    try:
        # Update the S3 object storage class to GLACIER
        response = s3.put_object(
            Bucket=archive_bucket,
            Key=source_key,
            StorageClass='GLACIER'
        )
        print(f'Successfully archived {source_key} to Glacier:', response)
    except Exception as e:
        print(f'Error archiving {source_key} to Glacier:', e)
        raise
