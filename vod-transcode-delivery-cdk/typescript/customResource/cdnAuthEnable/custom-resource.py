import json
import boto3
import uuid

sm = boto3.client('secretsmanager')
def on_event(event, context):
  physical_id = context.log_stream_name
  props = event["ResourceProperties"]
  enable_cdn_auth = props["EnableCdnAuth"]
  if enable_cdn_auth != "true":
    return {'PhysicalResourceId': physical_id}
  
  request_type = event['RequestType']
  if request_type == 'Create': return on_create_update(event,physical_id)
  if request_type == 'Update': return on_create_update(event,physical_id)
  if request_type == 'Delete': return on_delete(event)
  raise Exception("Invalid request type: %s" % request_type)

import random
import string

def get_random_string(length):
    # With combination of lower and upper case
    result_str = ''.join(random.choice(string.ascii_letters) for i in range(length))
    # print random string
    return result_str

def on_create_update(event,physical_id):
  uuid_ = str(uuid.uuid4())
  secret = {"MediaPackageCDNIdentifier": uuid_}
  return auth_secret(secret,physical_id)

  
def auth_secret(secret, physical_id):
  try: 
    response = sm.create_secret(
      Name="/vod/cdn_auth_ap-southeast-2/"+get_random_string(5),
      SecretString= json.dumps(secret)
    )

    secret_arn = response["ARN"]

    return {
      "PhysicalResourceId": physical_id,
      "Data":{
        "SecretArn": secret_arn
       }
      }
  
  except Exception as error: 
    raise error
  
def on_delete(event):
  physical_id = event["PhysicalResourceId"]
  return { 'PhysicalResourceId': physical_id }