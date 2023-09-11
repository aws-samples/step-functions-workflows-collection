import json
import boto3
import os

table_name = os.environ['TABLE_NAME']

client = boto3.client('ses')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    

    # Get detailType and cart id
    body = json.loads(event["Records"][0]["body"])
    detailType = body["detail-type"]
    cart_id = body["detail"]["cart_id"]
    
    # Retrieve user's email from dynamodb Table
    response = table.get_item(
    Key={
        "cart_id" : cart_id
    })
    
    # make sure both emails are verified in SES
    DESTINATION_EMAIL = response["Item"]['email']
    SOURCE_EMAIL = "add_your_email@email.com"


    if detailType == "PaymentFailed":
        response = client.send_email(
            Source= SOURCE_EMAIL,
            Destination={
                'ToAddresses': [
                    DESTINATION_EMAIL,
                ]},
            Message={
                'Subject': {
                    'Data': "Octank's Payment Failed",
                },
                'Body': {
                    'Text': {
                        'Data': "Hello, your payment to Octank is unsuccessful. Please try again.",
                    },
                }
            })
    elif detailType == "ShippingFailed":
        response = client.send_email(
            Source= SOURCE_EMAIL,
            Destination={
                'ToAddresses': [
                    DESTINATION_EMAIL,
                ]},
            Message={
                'Subject': {
                    'Data': "Octank's Order Confirmed",
                },
                'Body': {
                    'Text': {
                        'Data': "Hello, your order is confirmed. Shipping details will arrive shortly."
                    },
                }
            })
    elif detailType == "ShippingSuccessful":
        response = client.send_email(
            Source= SOURCE_EMAIL,
            Destination={
                'ToAddresses': [
                  DESTINATION_EMAIL,
                ]},
            Message={
                'Subject': {
                    'Data': "Octank's Order Confirmed",
                },
                'Body': {
                    'Text': {
                        'Data': "Hello, your order is confirmed. Please refer to shipping email for more details."
                    },
                }
            })
    
    return {
        'statusCode': 200,
        'body': json.dumps(detailType)
    }
