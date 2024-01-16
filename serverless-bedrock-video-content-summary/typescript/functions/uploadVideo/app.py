import boto3
import json
import os
from botocore.config import Config
import uuid 

source_bucket = os.environ['SOURCE_BUCKET']
destination_bucket = os.environ['DESTINATION_BUCKET']
table_name = os.environ['DDB_TABLE_NAME']
sns_topic_arn = os.environ['SNS_TOPIC_ARN']
# config = Config(signature_version='s3v4')
region = os.environ['AWS_DEFAULT_REGION']
dynamodb_client = boto3.resource('dynamodb')
table = dynamodb_client.Table(table_name)
# s3_client = boto3.client('s3', config=config, region_name=os.environ['AWS_DEFAULT_REGION'])
sns_client = boto3.client('sns')
s3_client = boto3.client('s3', region_name=region, config=Config(signature_version='s3v4', use_dualstack_endpoint=True, s3={'addressing_style': 'virtual'}))
video_id = str(uuid.uuid1())

def lambda_handler(event, context):
    file_name = event['headers']['filename']
    file_type = event['headers']['video-format']
    presigned_url = ''
    try:
        # Generate the presigned url for uploading the video
        if file_type != 'video/mp4':
            presigned_url = s3_client.generate_presigned_url('put_object', Params={'Bucket': source_bucket, 'Key': file_name}, ExpiresIn=3600, HttpMethod='PUT')
        else: 
            presigned_url = s3_client.generate_presigned_url('put_object', Params={'Bucket': destination_bucket, 'Key': 'dirtct_upload/'+video_id+'.mp4'}, ExpiresIn=3600, HttpMethod='PUT')
            video_name = file_name
            job_status = 'NULL'
            item = {
                'video_id': video_id,
                'video_name': video_name,
                'job_status': job_status
            }
            try:
                table.put_item(Item=item)
                sns_client.publish(
                    TopicArn=sns_topic_arn,
                    Message=str(item)
                )
            except Exception as e:
                raise e


        return {
            'statusCode': 200,
            'body': json.dumps({
                'upload_url': presigned_url
            }),
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Content-Type': 'application/json',
            }
        }
        

    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps('Internal server errorrrrr'),
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Content-Type': 'application/json',
            }
        }
