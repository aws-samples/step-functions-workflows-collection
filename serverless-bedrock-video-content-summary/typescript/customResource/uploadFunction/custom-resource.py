import boto3
import os
from urllib.parse import unquote_plus
import time
s3_client = boto3.client('s3')
cf_clinet = boto3.client('cloudfront')
bucket = os.environ['WEBSITE_BUCKET']
api_endpoint = os.environ['API_ENDPOINT']
destribution_id = os.environ['DISTRIBUTION_ID']

def on_event(event, context):
    physical_id = context.log_stream_name
    request_type = event['RequestType']
    try:
        if request_type == 'Create':
            return on_create_update()
        if request_type == 'Update':
            return on_create_update()
        if request_type == 'Delete':
            return on_delete()
    except Exception as e: 
        raise e


def on_create_update():
    # Download the upload-script.js from the deployment package
    s3_client.download_file(bucket, 'upload-script.js', '/tmp/upload-script.js')

    # Replace the placeholder with the actual API Gateway URL
    with open('/tmp/upload-script.js', 'r') as file:
        file_contents = file.read()

    file_contents = file_contents.replace('__API_ENDPOINT__', api_endpoint)

    with open('/tmp/index-modified.html', 'w') as file:
        file.write(file_contents)

    # Upload the modified upload-script.js back to the S3 bucket
    s3_client.upload_file('/tmp/index-modified.html', bucket, 'upload-script.js', ExtraArgs={'ContentType': 'text/html'})

    # create invalidation in the cloudfront distribution after inject the api endpoint
    time.sleep(5)
    cf_clinet.create_invalidation(
        DistributionId = destribution_id,
        InvalidationBatch = {'Paths': {
                'Quantity': 1,
                'Items': [
                    '/*'
                ]
            },
            'CallerReference': str(time.time()).replace('.', '')

        },
    )

def on_delete():
    pass
