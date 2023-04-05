import os
import io
import pandas as pd
import boto3
import json
import matplotlib.pyplot as plt
import datetime

DATA_BUCKET = os.environ["DATA_BUCKET"]
s3 = boto3.client("s3")

"""
Lambda function that reads the output files from the Monte Carlo simulation and aggregates them into a single file.
@param event: The event object that contains the prefix and the number of samples to aggregate.
@return: Pre-signed URLs to the aggregated file and the line graph of the aggregated data.
"""
def lambda_handler(event, context):
    print(f"{json.dumps(event)}")
    bucket_name = DATA_BUCKET
    prefix = event['prefix']
    number_of_samples = event['number_of_samples']

    result = aggregate(bucket_name=bucket_name, prefix=prefix, number_of_samples=number_of_samples)
   
    return result

"""
Aggregates the output files from the Monte Carlo simulation into a single file, and produces a line graph of the aggregated data.
@param bucket_name: The name of the S3 bucket.
@param prefix: The prefix of the Monte Carlo simulation outputs.
@param number_of_samples: The number of Monte Carlo simulation outputs to aggregate.
"""
def aggregate(bucket_name, prefix, number_of_samples):
    print(f"Aggregating {number_of_samples} samples from {prefix}")
    dfs = []
    for i in range(number_of_samples):
        df = read_df(bucket_name, f"{prefix}/outputs/{i}.csv")
        dfs.append(df)
    
    plt.rcParams["figure.autolayout"] = True
    plt.rcParams["figure.figsize"] = [10, 5]
    # plt.style.use('dark_background')
    plt.title("Monte Carlo simulation results graph")
    plt.xlabel("Time Steps (months)")
    plt.ylabel("Revenue (USD)")
    # plt.grid(True)

    for i, serie in enumerate(dfs):
        plt.plot(serie, color='lightgrey')

    df = pd.concat(dfs, axis=1)
    df["p50"] = df.quantile(0.5, axis=1)
    df["p10"] = df.quantile(0.10, axis=1)
    df["p90"] = df.quantile(0.90, axis=1)

    plt.plot(df["p50"], label='p50')
    plt.plot(df["p10"], label='p10')
    plt.plot(df["p90"], label='p90')
    plt.legend()

    img_data = io.BytesIO()
    plt.savefig(img_data, format="png", dpi=300)
    plt.close()
    timestamp = datetime.datetime.now().timestamp()
    graph_key = f"{prefix}/plot{timestamp}.png"
    write_image_to_s3(bucket_name, graph_key, img_data)
    aggregated_result_csv = f"{prefix}/aggregated_results.csv"
    write_df(bucket_name, aggregated_result_csv, df)

    presigned_csv_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": aggregated_result_csv},
        ExpiresIn=3600,
    )
    presigned_graph_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": graph_key},
        ExpiresIn=3600,
    )

    return {
        "graph_presigned_url": presigned_graph_url,
        "csv_presigned_url": presigned_csv_url,
    }


def read_df(bucket:str, key:str) -> pd.DataFrame:
    get_response = s3.get_object(Bucket=bucket, Key=key)
    status = get_response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    if status != 200:
        raise (f"S3 get_object fail. Status - {status}")
    df = pd.read_csv(get_response.get("Body"), index_col=0)
    return df

def write_df(bucket: str, key:str, df: pd.DataFrame):
    with io.StringIO() as csv_buffer:
        df.to_csv(csv_buffer)
        response = s3.put_object(
            Bucket=bucket, Key=key, Body=csv_buffer.getvalue()
        )
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status != 200:
            print(f"Unsuccessful S3 put_object response. Status - {status}")

def write_image_to_s3(bucket_name, graph_key, img_data):
    img_data.seek(0)
    response = s3.put_object(
        Bucket=bucket_name, Body=img_data, ContentType="image/png", Key=graph_key
    )
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    if status != 200:
        print(f"Unsuccessful S3 put_object response. Status - {status}")
