import boto3
import os

ddb = boto3.client('dynamodb')
table_name = os.environ.get('TABLE_NAME')

def handler(event, context):
    print(event)
    connection_id = event['requestContext']['connectionId']
    domain_name = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    add_connection_id(connection_id, domain_name, stage)
    return {
        'statusCode': 200
    }

def add_connection_id(connection_id, domain_name, stage):
    print(connection_id)
    ddb.put_item(
        TableName=table_name,
        Item={
            'connectionId': {'S': connection_id},
            'domainName': {'S': domain_name},
            'stage': {'S': stage}
        }
    )
