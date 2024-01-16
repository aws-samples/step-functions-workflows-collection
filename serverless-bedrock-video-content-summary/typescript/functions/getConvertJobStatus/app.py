import json
import boto3
import os

# media convert boto 3 client setup
region = os.environ["AWS_DEFAULT_REGION"]
endpoints = boto3.client("mediaconvert", region_name=region).describe_endpoints()
media_convert = boto3.client("mediaconvert", region_name=region, endpoint_url=endpoints["Endpoints"][0]["Url"], verify=False)
def lambda_handler(event, context):
    job_id = event["invocation_id"]
    video_id = event["video_id"]
    source_s3_key = event["source_s3_key"]
    source_s3_bucket = event["source_s3_bucket"]
    results=event["results"]
    try:
        # Retrive job status
        response = media_convert.get_job(Id=job_id)
        job_status = response["Job"]["Status"]
        return {
                "video_id": video_id,
                "invocation_id": job_id,
                "job_status": job_status,
                "source_s3_bucket": source_s3_bucket,
                "source_s3_key": source_s3_key,
                "results": results
            }
        if job_status == "ERROR" or "CANCELED":
            raise 

    except Exception as error: 
        raise error 
    