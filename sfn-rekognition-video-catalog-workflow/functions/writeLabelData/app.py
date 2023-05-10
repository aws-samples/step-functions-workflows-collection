import json
import boto3
from botocore.exceptions import ClientError
import os, tempfile
import pandas as pd
import uuid
import datetime


s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('videoContentMetaData')

video_src_bucket = os.environ['video_src_bucket']
video_metadata_lake_bucket = os.environ['video_metadata_lake_bucket']

def lambda_handler(event, context):
    parse_json(event)
    #print(datetime.datetime.now())
    
def load_from_s3(event):
    data = s3.get_object(Bucket='video-rekognition-outputs', Key=event['key'])
    content = data['Body'].read()
    jsonData = json.loads(content)
    return jsonData
    
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
    
   
    

def parse_json(data):
    Items = []
    labels = data['Results']['Labels']
    filename = data['Key']
    executionId = data['executionId']
    
    for label in labels:
        Categories = ""
        for category in label['Label']['Categories']:
            #print(category['Name'])
            Categories += category['Name'] + '|'
        
        Parent=""    
        for parent in label['Label']['Parents']:
            Parent += parent['Name'] + '|'
            
        Label=""    
        Label = label['Label']['Name']
        StartTimestampMillis = label['StartTimestampMillis']
        DurationMillis = label['DurationMillis']
        EndTimestampMillis = label['EndTimestampMillis']
        Timestamp = label['Timestamp']
        Item = {
            'video':filename,
            'label':Label,
            'Categories':Categories,
            'Parents':Parent,
            'Timestamp':Timestamp,
            'StartTimestampMillis':StartTimestampMillis,
            'DurationMillis':DurationMillis,
            'EndTimestampMillis':EndTimestampMillis
        }
        
        Items.append(Item)
    try:
        write_to_csv(Items, filename, executionId)
        update_s3_object_tagging(filename,executionId)
        
    except ClientError:
        print("Couldn't load data into table %s.", table.name)
        raise
    
    
def write_to_csv(Items, filename, executionId):
    df = pd.DataFrame(Items)
    tmpFile = '/tmp/' + filename + '.csv'
    
    df.to_csv(tmpFile, encoding='utf-8', index=False)
    bucket = video_metadata_lake_bucket
    folder = executionId
    s3Path = 'labels/' + folder +'/' + filename + '.csv'
    s3 = boto3.resource("s3")
    s3.Bucket(bucket).upload_file(tmpFile, s3Path)
    os.remove(tmpFile)