import json

import random

class OK:
    message = "OK"
    statusCode = 200
    
class BadRequest(Exception):
    message = "BadRequest"
    statusCode = 400
    
class InternalServerError(Exception):
    message = "InternalServerError"
    statusCode = 500
    


def lambda_handler(event, context):
    responses = [OK, BadRequest, InternalServerError]
    random_response = random.randint(0,2)
    response = responses[random_response]
    if response.statusCode == 200:
        return { 
            "statusCode": response.statusCode, 
            "body": json.dumps({
                "message": response.message
            })
        }
    else:
        raise response
