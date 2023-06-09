""" 
Sample Lambda function that accepts 'expirydate' as input. 
It calculates and return the time difference between the current date and the input date.
"""

import json, math
from datetime import datetime

def lambda_handler(event, context):
    print(event)
    expirydate=event['expirydate']
    expiry_date = datetime.strptime(expirydate, '%Y-%m-%dT%H:%M:%SZ')
    timestamp = math.ceil((expiry_date - datetime.now()).total_seconds())
    return {
        "expirydate": timestamp,
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
