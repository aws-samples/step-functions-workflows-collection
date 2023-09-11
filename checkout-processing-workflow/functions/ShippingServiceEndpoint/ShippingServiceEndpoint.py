import json
import boto3

step_function_client = boto3.client("stepfunctions")

def lambda_handler(event, context):
    
    body = json.loads(event['body'])
    payload = (body['Payload'])
    TaskToken = body['MyTaskToken']
    
    # Modify the Status variable to test out other branches in the workflow
    output = {
        "CartId" : payload['CartId'],
        "Status" : "ShippingSucccessful"
        #"Status" : "ShippingFailed"
    }
    
    output = json.dumps(output)
    
    #send the token to the Step Function
    step_function_client.send_task_success(
                taskToken=TaskToken,
                output=output,
    )

    return {
        'statusCode': 200
    }