import json
import boto3
import os

import botocore.response as br
from boto3.dynamodb.conditions import Key

sfn_client = boto3.client('stepfunctions')
dynamodb_tbl = os.environ['dynamo_db_table']

ddb_table = boto3.resource('dynamodb').Table(dynamodb_tbl)

def lambda_handler(event, context):
    # TODO implement
    #print(event)
    parse_event(event)
   
    
def parse_event(event):
    for record in event['Records']:
        message = json.loads(record['Sns']['Message'])
        job_id = message['JobId']
        print('JobId',job_id, sep=": ")
        taskToken = get_record(job_id)
        print('taskToken',taskToken,sep=": ")
        #send callback to statemachine now to continue processing
        status = message['Status']
        if message['Status'] == 'SUCCEEDED':
            print('sending success callback')
            data = json.dumps(message)
            sendTaskSuccess(taskToken,data)

def get_record(job_id):
    records = ddb_table.query(
        IndexName='jobid-index',
        KeyConditionExpression=Key('jobid').eq(job_id),
        ProjectionExpression='taskToken')
    print('Records',records,sep=": ")
    if 'Items' in records:
        taskToken = records['Items'][0]['taskToken']
        return taskToken
    else:
        print('no records returned')
        return ''
    
        
        
def sendTaskSuccess(taskToken,message):
    response = sfn_client.send_task_success(
    taskToken=taskToken,
    output=message
)

def sendTaskFailure(taskToken):
    response = client.send_task_failure(
    taskToken='string',
    error='string',
    cause='string'
)