import os
import io
import numpy as np
import pandas as pd
import datetime
import boto3
import asyncio
import functools
from botocore.config import Config

DATA_BUCKET = os.environ['DATA_BUCKET']
config = Config(
    retries={
        'max_attempts': 10,
        'mode': 'standard'
    }
)
s3 = boto3.client("s3", config=config)

"""
This lambda function is used to generate samples from a given production array and unit price.
@param event: The event object passed in for lambda invocation.
"""
def lambda_handler(event:dict, context:dict):
    production_array = np.array(event['monthly_production'])
    unit_price = event['unit_price']
    change_mean = event['mean_price_change']
    change_std = event['standard_deviation']
    number_of_samples = event['number_of_samples']
    bucket_name = DATA_BUCKET
    prefix = generate_prefix()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        generate_samples(production_array, unit_price, change_mean, change_std, number_of_samples, bucket_name, prefix)
    )
    

    result = {
        "number_of_samples": number_of_samples,
        "bucket_name": bucket_name,
        "prefix": prefix,
        "inputprefix": f"{prefix}/inputs",
    }
    return result

"""
This function is used to generate a prefix for the samples.
@return: A string containing the prefix.
"""
def generate_prefix(): 
    now = datetime.datetime.now()
    return now.strftime("%Y%m%d%H%M")

"""
This function is used to generate samples from a given production array and unit price.
@param production_array: The production array.
@param unit_price: The unit price.
@param change_mean: The mean of the price change.
@param change_std: The standard deviation of the price change.
@param number_of_samples: The number of samples to generate.
@param bucket_name: The name of the S3 bucket.
@param prefix: The prefix for the S3 objects.
"""
async def generate_samples(production_array, unit_price, change_mean, change_std, number_of_samples, bucket_name, prefix):
    size = len(production_array)
    
    loop = asyncio.get_running_loop()
    def generate_sample(index):
        dx = np.random.normal(change_mean, change_std, size)
        price_array = unit_price + np.cumsum(dx)
        df = pd.concat([pd.Series(production_array), pd.Series(price_array)], axis=1)
        key = f"{prefix}/inputs/{index}.csv"
        return loop.run_in_executor(None, functools.partial(
            write_df, bucket=bucket_name, key=key, df=df
        ))

    await asyncio.gather(*list(map(generate_sample, range(number_of_samples))))

"""
This function is used to write a dataframe to S3 as a CSV file.
@param bucket: The name of the S3 bucket.
@param key: The key for the S3 object.
@param df: The dataframe to write.
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
