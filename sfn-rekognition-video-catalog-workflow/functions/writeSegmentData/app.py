import json
import boto3
from botocore.exceptions import ClientError
import os, tempfile
import pandas as pd
import uuid

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('video_metadata')

video_src_bucket = os.environ['video_src_bucket']
video_metadata_lake_bucket = os.environ['video_metadata_lake_bucket']

def lambda_handler(event, context):
    parse_json(event)
    
def parse_json(data):
    putItems=[]
    key = str(data['Key'])
    executionId = data['executionId']
   
    segments = data['Results']['Segments']
    for segment in segments:
        #print(segment)
        segment['video']=key
        if 'TechnicalCueSegment' in segment:
            print(segment['TechnicalCueSegment']['Type'])
            segment['TechnicalCueSegment'] = segment['TechnicalCueSegment']['Type']
        else:
            segment['TechnicalCueSegment'] = 'null'
            
        if 'ShotSegment' in segment:
            segment['ShotSegment'] = segment['ShotSegment']['Index']
        else:
            segment['ShotSegment'] = 'null'
   
        putItems.append(segment)    

    write_to_csv(putItems, key, executionId)
    update_s3_object_tagging(key,executionId)
    
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
    

def write_to_csv(Items, filename, executionId):
    df = pd.DataFrame(Items)
    
    tmpFile = '/tmp/' + filename + '.csv'
    
    df.to_csv(tmpFile, encoding='utf-8', index=False)
    bucket = video_metadata_lake_bucket
    s3Path = 'segments/' + executionId + '/' + filename + '.csv'
    
    s3 = boto3.resource("s3")
    s3.Bucket(bucket).upload_file(tmpFile, s3Path)
    
    os.remove(tmpFile)
    