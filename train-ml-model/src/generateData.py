import boto3
import random
import csv
import json
from os import environ

RANGE_BEGIN = 0
RANGE_END = 100
NUM_EXAMPLES = 5000



def f(x, y):
    return int(y >= (3 * x + 5))

def handler(event, context):
    s3 = boto3.resource('s3')
    base_key = 'csv/'

    train_points = [(random.randint(RANGE_BEGIN, RANGE_END), random.randint(RANGE_BEGIN, RANGE_END)) for i in range(NUM_EXAMPLES)]
    train = [[f(x, y), x, y] for x, y in train_points]
    test = [[random.randint(RANGE_BEGIN, RANGE_END), random.randint(RANGE_BEGIN, RANGE_END)] for i in range(NUM_EXAMPLES)]
    bucket_name = environ.get("S3_BUCKET_NAME","NONE")
    bucket = s3.Bucket(bucket_name)
    
    with open('/tmp/train.csv', 'w') as writeFile:
        writer = csv.writer(writeFile)
        writer.writerows(train)

    with open('/tmp/test.csv', 'w') as writeFile:
        writer = csv.writer(writeFile)
        writer.writerows(test)
    
    bucket.upload_file('/tmp/train.csv', base_key + 'train.csv')
    bucket.upload_file('/tmp/test.csv', base_key + 'test.csv')

    return {
        'statusCode': 200,
        'body': json.dumps({
            'train': base_key + 'train.csv',
            'test': base_key + 'test.csv',
            's3bucket': bucket_name
        })
    }