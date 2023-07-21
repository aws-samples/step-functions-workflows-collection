import os
import boto3
import json

#detect image label using rekognition
def detect_labels(bucket, fname):
    client=boto3.client('rekognition')
    try:
        response = client.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':fname}}, MaxLabels=30)
    except Exception as error:
        print(error)
        return 'Error detecting labels in photo'
    return response['Labels']

def lambda_handler(event, context):
    bucket = event['Bucket']
    fname = event['FileName']

    labels = detect_labels(bucket=bucket, fname=fname) 

    #return S3 name, file name and labels
    response = json.dumps({
        'Bucket': bucket,
        'FileName': fname,
        'Labels': labels
    })
    return json.loads(response)
