import os
import io
import pandas as pd
import boto3


DATA_BUCKET = os.environ["DATA_BUCKET"]
s3 = boto3.client("s3")

"""
Lambda function to calculate the revenue as a product of production and price
@param event: event object from lambda invocation with the Key of the file to be processed
"""
def lambda_handler(event, context):
    bucket_name = DATA_BUCKET
    key = event['Key']

    calculate(bucket_name=bucket_name, key=key)

    return key

"""
Function to calculate the revenue as a product of production and price
@param bucket_name: name of the bucket
@param key: key of the file to be processed
"""
def calculate(bucket_name, key):
    df = read_df(bucket=bucket_name, key=key)
    prefix = key.split('/')[0]
    file_name = key.split('/')[-1]
    column_name = f"r_{file_name.split('.')[0]}"
    output_key = f"{prefix}/outputs/{file_name}"

    df[column_name] = df['0'] * df['1']
    
    write_df(bucket=bucket_name, key=output_key, df=df[column_name])
    
"""
Function to read a CSV file from S3 into a pandas dataframe
@param bucket: name of the bucket
@param key: key of the file to be processed
@return: pandas dataframe
"""
def read_df(bucket:str, key:str) -> pd.DataFrame:
    get_response = s3.get_object(Bucket=bucket, Key=key)
    status = get_response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    if status != 200:
        raise (f"S3 get_object fail. Status - {status}")
    df = pd.read_csv(get_response.get("Body"), index_col=0)
    return df

"""
Function to write a pandas dataframe to a CSV file in S3
@param bucket: name of the bucket
@param key: key of the file to be processed
@param df: pandas dataframe
"""
def write_df(bucket: str, key:str, df: pd.DataFrame):
    with io.StringIO() as csv_buffer:
        df.to_csv(csv_buffer)
        response = s3.put_object(
            Bucket=bucket, Key=key, Body=csv_buffer.getvalue()
        )
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status != 200:
            print(f"Unsuccessful S3 put_object response. Status - {status}")
