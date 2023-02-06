import boto3
import os

ddb = boto3.client('dynamodb')
table_name = os.environ.get('TABLE_NAME')

def handler(event, context):
    connection_id = event['requestContext']['connectionId']
    delete_connection_id(connection_id)
    return {
        'statusCode': 200
    }

def delete_connection_id(connection_id):
    ddb.delete_item(
        TableName=table_name,
        Key={
            'connectionId': {'S': connection_id}
        }
    )

