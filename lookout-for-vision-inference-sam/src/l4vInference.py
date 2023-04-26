import json
import urllib.parse
import boto3
import base64
import os
import logging

LFV_PROJECT_NAME = os.environ['L4V_PROJECT']
LFV_MODEL_VERSION = os.environ['L4V_MODEL_VERSION']
REGION = os.environ.get('REGION', 'eu-west-1')
# Initiate clients
lookoutvision = boto3.client('lookoutvision')
s3 = boto3.client('s3')

def handler(event, context):

    print(event)
    bucket = event["detail"]["bucket"]["name"]
    key = event["detail"]["object"]["key"]
    is_anomalous = detect_anomalies(bucket, key)
    response = {}
    jsondata = {}
    response['anomalous'] = is_anomalous
    copysource = "/" + bucket + "/" + key
    response['newkeyname'] = key
    jsondata['response'] = response
    jsondata['copysource'] = copysource
    return jsondata


def detect_anomalies(bucket, key):
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        project_name = LFV_PROJECT_NAME
        model_version = LFV_MODEL_VERSION
        content_type = response['ContentType']
        image = response['Body']
        image_body = image.read()


        lookout_response = lookoutvision.detect_anomalies(
            ProjectName=project_name,
            ModelVersion=model_version,
            Body=image_body,
            ContentType=content_type
        )

        is_anomalous = lookout_response['DetectAnomalyResult']['IsAnomalous']

        return is_anomalous

    except Exception as e:

        print(e)
        raise e