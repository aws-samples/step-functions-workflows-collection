from warnings import catch_warnings
import boto3
import os
import sys
import uuid
from urllib.parse import unquote_plus
from PIL import Image
import PIL.Image
            
s3_client = boto3.client('s3')
            
def resize_image(image_path, resized_path):
    width = os.environ.get('Width')
    if width is None:
        width = 100
    else:
        width = int(width)

    height = os.environ.get('Height')
    if height is None:
        height = 100
    else:
        height = int(height)
    
    Size = (width, height)

    with Image.open(image_path) as image:
        #image.thumbnail(tuple(x / 2 for x in image.size))
        image.thumbnail(Size)
        image.save(resized_path)

    
            
def lambda_handler(event, context):
    bucket = event['detail']['bucket']['name']
    key = unquote_plus(event['detail']['object']['key'])
    tmpkey = key.replace('/', '')
    download_path = '/tmp/{}{}'.format(uuid.uuid4(), tmpkey)
    upload_path = '/tmp/resized-{}'.format(tmpkey)
    s3_client.download_file(bucket, key, download_path)
    resize_image(download_path, upload_path)
    s3_client.upload_file(upload_path, '{}-resized'.format(bucket), 'resized-{}'.format(key))
    
    outputMetadata = {}
    outputMetadata["sourcebucketName"]= event["detail"]["bucket"]["name"]
    outputMetadata["sourceobjectName"]= event["detail"]["object"]["key"]
    outputMetadata["sourceobjectSize"]= event["detail"]["object"]["size"]
    outputMetadata["destbucketName"]= '{}-resized'.format(bucket)
    outputMetadata["destdestobjectName"]= 'resized-{}'.format(key)
    
    return outputMetadata,event
    
    