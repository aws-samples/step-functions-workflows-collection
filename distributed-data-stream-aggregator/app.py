import sys
import boto3
import pandas as pd
import os
import json
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from pyspark.context import SparkContext
import logging

# Configure the logger
logging.basicConfig(level=logging.ERROR)
log = logging.getLogger(__name__)

def get_s3_client():
    """Returns the S3 client"""
    return boto3.client("s3")


def get_input_files(s3_client, bucket, input_prefix):
    """List JSON files in the input path"""
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=input_prefix)
    return [obj["Key"] for obj in response.get("Contents", []) if obj["Key"].endswith(".json")]


def read_json_from_s3(s3_client, bucket, file_key):
    """Read JSON data from a file in S3"""
    obj = s3_client.get_object(Bucket=bucket, Key=file_key)
    json_content = obj['Body'].read().decode('utf-8')
    decoded_json = json.loads(json_content)  # First decode
    if isinstance(decoded_json, str):
        decoded_json = json.loads(decoded_json)  # Second decode if still a string
    return decoded_json

def merge_json_data(files, s3_client, bucket):
    """Merge multiple JSON files into a single DataFrame"""
    dataframes = []
    for file in files:
        try:
            decoded_json = read_json_from_s3(s3_client, bucket, file)
            if isinstance(decoded_json, list):
                json_df = pd.DataFrame(decoded_json)
                dataframes.append(json_df)
            else:
                log.warning(f"Unexpected JSON format in file {file}, skipping.")
        except json.JSONDecodeError as e:
            log.error(f"Error decoding JSON from file {file}: {e}")
            raise e
    if dataframes:
        return pd.concat(dataframes, ignore_index=True)
    else:
        return None


def save_to_csv(dataframe, output_file):
    """Save DataFrame to CSV"""
    try:
        dataframe.to_csv(output_file, index=False, sep=",", quoting=1, escapechar="\\")
    except Exception as e:
        log.error(f"Error saving merged file locally: {e}")
        sys.exit(1)


def upload_to_s3(s3_client, local_file, bucket, output_file, task_id):
    """Upload the CSV file to S3"""
    try:
        s3_client.upload_file(
            local_file, bucket, output_file,
            ExtraArgs={"Metadata": {"task_id": task_id}}
        )
        log.debug(f"Merged CSV uploaded to s3://{bucket}/{output_file}")
    except Exception as e:
        log.error(f"Error uploading file to S3: {e}")
        sys.exit(1)


def delete_s3_files(s3_client, bucket, files):
    """Delete processed files from S3"""
    try:
        for file in files:
            s3_client.delete_object(Bucket=bucket, Key=file)
            log.debug(f"Deleted: s3://{bucket}/{file}")
    except Exception as e:
        log.error(f"Error deleting temporary files: {e}")
        sys.exit(1)


def cleanup_local_file(local_output_file):
    """Remove the local output file"""
    if os.path.exists(local_output_file):
        os.remove(local_output_file)


def main():
    # Avoid multiple SparkContext initialization
    sc = SparkContext.getOrCreate()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session

    # Get parameters
    args = getResolvedOptions(sys.argv, ["task_id", "bucket", "output_file_name"])
    task_id = args["task_id"]
    bucket = args["bucket"]
    output_file = args["output_file_name"]
    local_output_file = f"/tmp/{output_file}"

    # S3 Client
    s3_client = get_s3_client()

    # Define input path in S3
    input_prefix = f"tmp/{task_id}/"

    # List all JSON part files under the input path
    files = get_input_files(s3_client, bucket, input_prefix)

    if not files:
        log.debug("No JSON files found to process.")
        sys.exit("No JSON files found to process.")  # Exit with a message

    log.debug(f"Processing JSON files: {files}")

    # Merge the JSON files into a single DataFrame
    merged_df = merge_json_data(files, s3_client, bucket)

    if merged_df is None:
        log.debug("No valid JSON data to merge.")
        sys.exit("No valid JSON data to merge.")  # Exit with a message

    # Check column count before assigning headers
    expected_columns = ["discount_code", "error_message", "status"]
    if merged_df.shape[1] == len(expected_columns):
        merged_df.columns = expected_columns

    # Save merged CSV to local storage
    save_to_csv(merged_df, local_output_file)

    # Upload merged CSV to S3
    upload_to_s3(s3_client, local_output_file, bucket, output_file, task_id)

    # Delete temporary files from S3
    delete_s3_files(s3_client, bucket, files)

    # Cleanup local temp file if it exists
    cleanup_local_file(local_output_file)

    # Print the output file location (for Step Function)
    log.debug(f"Output file: s3://{bucket}/{output_file}")

    log.debug("Process completed successfully!")


if __name__ == "__main__":
    main()
