import json
import boto3
import os
s3 = boto3.client('s3')

video_src_bucket = os.environ['video_src_bucket']
video_processed_bucket = os.environ['video_processed_bucket']

def lambda_handler(event, context):
    items = event['Items']
    executionId = event['executionId']
    
    for item in items:
        #check if tag exsits
        get_object_tags(item['Key'])
        
def get_object_tags(key):
    response = s3.get_object_tagging(
        Bucket=video_src_bucket,
        Key=key)
    print(response)
    if 'TagSet' in response:
        tags = response['TagSet']
        for tag in tags:
            if tag['Key'] == 'MetadataLocationId':
                #tags exist continue moving otherwise leave the file alone because it has to be processed
                print('file was processed...move to archive')
                move_to_processed_bucket(key,tag['Value'])
                break;
        
def move_to_processed_bucket(filename, metadataFilePointer):
    print(filename, metadataFilePointer)
    copyRs = s3.copy_object(
        Bucket=video_processed_bucket,
        CopySource=video_src_bucket + '/' + filename,
        Key=filename,
        MetadataDirective = 'REPLACE',
        Metadata={
            'video-metadata-location':metadataFilePointer
        })
    
    if copyRs['ResponseMetadata']['HTTPStatusCode'] == 200: 
        deleteRs =s3.delete_object(Bucket=video_src_bucket, Key=filename)
        print(deleteRs)