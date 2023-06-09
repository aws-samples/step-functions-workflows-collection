import json
import boto3
from botocore.exceptions import ClientError
import os, tempfile
import pandas as pd

s3 = boto3.client('s3')
video_src_bucket = os.environ['video_src_bucket']
video_metadata_lake_bucket = os.environ['video_metadata_lake_bucket']

def lambda_handler(event, context):
    parse_json(event)

def parse_json(data):
    moderationLabels = data['Results']['ModerationLabels']
    filename = data['Key']
    executionId = data['executionId']
    
    write_to_csv(moderationLabels, filename, executionId)
    update_s3_object_tagging(filename,executionId)
    
def write_to_csv(Items, filename, executionId):
    df = pd.DataFrame(Items)
    
    tmpFile = '/tmp/' + filename + '.csv'
    
    df.to_csv(tmpFile, encoding='utf-8', index=False)
    bucket = video_metadata_lake_bucket
    s3Path = 'contentmoderated/' + executionId + '/' + filename + '.csv'
    
    s3 = boto3.resource("s3")
    s3.Bucket(bucket).upload_file(tmpFile, s3Path)
    
    os.remove(tmpFile)
    
def update_s3_object_tagging(filename, metadataFilePointer):
    copyRs = s3.put_object_tagging(
        Bucket=video_src_bucket,
        Key=filename,
        Tagging= {
            'TagSet':[{
                'Key':'MetadataLocationId',
                'Value':metadataFilePointer
            }]
        }
        )        