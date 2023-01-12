import json
import datetime
import sys
import boto3
import decimal
from boto3.dynamodb.conditions import Key, Attr
dynamodb_client = boto3.resource('dynamodb')
import re
import os

class Product(object):
    def __init__(self, ProductId, Quantity,UnitPrice,Size, Color,State):
        self.ProductId = ProductId
        self.Quantity = Quantity
        self.UnitPrice = UnitPrice
        self.Size = Size
        self.Color = Color
        self.State = State
      
def lambda_handler(event, context):

    """Sample Lambda function which mocks the operation of business process post receiving product inventory.

    For demonstration purposes, this Lambda function does not actually perform any
    actual transactions. It simply retrives the quantity and adds it to available quantity.

    Parameters
    ----------
    event: 
        Input product inventory event to the Lambda function

    context: object, required
        Lambda Context runtime methods and attributes

    Returns
    ------
        product_id, event json, timestamp and updated product json
    """
 
    inputEvent=event.get("ProductEvent")
    productId = inputEvent.get("productId")
    quantity = inputEvent.get("quantity")
    event_store_table=os.environ["EVENT_STORE_TABLE"]
   
    #check if record with input product_id already exists in the product event store
    table = dynamodb_client.Table(event_store_table)
    response = table.query(KeyConditionExpression=Key('Product_Id').eq(productId))
    items = response['Items']

    if items:
        for item in items:
            productDetails = item['Product_Details']
            productJson =json.loads (productDetails)
            productObject = Product(**productJson)
            productObject.Quantity=str(decimal.Decimal( productObject.Quantity)+decimal.Decimal(quantity))
            newProductJson=json.dumps(productObject.__dict__)
    else:
        productObject = Product(inputEvent.get("productId"),inputEvent.get("quantity"),inputEvent.get("unitPrice"),inputEvent.get("size"),inputEvent.get("color"),"Available")
        newProductJson = json.dumps(productObject.__dict__)
        
   
    response = {
            "statusCode": 200,
            "Product_Id" : productId,
            "UpdatedProduct" : newProductJson,
            "Event" : str(inputEvent),
            "EventDateTime" : datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    return response