import boto3
import random
import csv
import json
import os

YEAR_RANGE_BEGIN = 0
YEAR_RANGE_END = 19
MAKE_RANGE_BEGIN = 0
MAKE_RANGE_END = 25
NUM_DATASETS = 20
BASE_YEAR = 2000
BASE_MAKE = 65
year = [BASE_YEAR + i for i in range(NUM_DATASETS)]
make = [BASE_MAKE + i for i in range(26)]
S3_BUCKET = os.environ['S3_BUCKET']

def lambda_handler(event, context):
  s3 = boto3.resource('s3')
  columns = [['year', 'grade']]
  datasets = [[year[random.randint(YEAR_RANGE_BEGIN, YEAR_RANGE_END)], chr(make[random.randint(MAKE_RANGE_BEGIN, MAKE_RANGE_END)])] for i in range(NUM_DATASETS)]
  csv_data = columns + datasets

  bucket_name = S3_BUCKET
  bucket = s3.Bucket(bucket_name)

  with open('/tmp/log.csv', 'w') as writeFile:
      writer = csv.writer(writeFile)
      writer.writerows(csv_data)

  bucket.upload_file('/tmp/log.csv', 'log/log.csv')

  return {
      'statusCode': 200,
      'body': json.dumps({
          'log': 'log/log.csv',
      })
  }