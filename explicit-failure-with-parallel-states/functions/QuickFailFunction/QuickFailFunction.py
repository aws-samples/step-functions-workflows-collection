import json

def lambda_handler(event, context):
    # TODO implement
    
    raise Exception("Throwing explicit error") 
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
