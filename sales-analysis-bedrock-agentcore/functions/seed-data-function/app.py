import boto3
import json
import urllib.request


def send(event, context, status, data={}):
    body = json.dumps({
        "Status": status,
        "Reason": "See CloudWatch",
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "Data": data,
    }).encode()
    urllib.request.urlopen(urllib.request.Request(
        event["ResponseURL"], data=body,
        headers={"Content-Type": ""}, method="PUT"
    ))


def handler(event, context):
    if event["RequestType"] == "Delete":
        send(event, context, "SUCCESS")
        return

    csv = (
        "region,product,quarter,revenue,units_sold,returns,customer_satisfaction\n"
        "North America,Widget Pro,Q1,245000,980,23,4.5\n"
        "North America,Widget Pro,Q2,312000,1250,18,4.7\n"
        "North America,Widget Lite,Q1,89000,1780,95,3.8\n"
        "North America,Widget Lite,Q2,94000,1920,88,3.9\n"
        "Europe,Widget Pro,Q1,187000,720,15,4.3\n"
        "Europe,Widget Pro,Q2,203000,790,12,4.6\n"
        "Europe,Widget Lite,Q1,56000,1120,67,3.6\n"
        "Europe,Widget Lite,Q2,61000,1200,54,3.7\n"
        "Asia Pacific,Widget Pro,Q1,134000,510,19,4.1\n"
        "Asia Pacific,Widget Pro,Q2,178000,690,14,4.4\n"
        "Asia Pacific,Widget Lite,Q1,72000,1440,82,3.5\n"
        "Asia Pacific,Widget Lite,Q2,88000,1760,71,3.7\n"
        "South America,Widget Pro,Q1,45000,170,8,4.0\n"
        "South America,Widget Pro,Q2,67000,260,6,4.2\n"
        "South America,Widget Lite,Q1,23000,460,35,3.4\n"
        "South America,Widget Lite,Q2,31000,620,28,3.6"
    )

    bucket = event["ResourceProperties"]["BucketName"]
    boto3.client("s3").put_object(
        Bucket=bucket,
        Key="sample-sales-data.csv",
        Body=csv.encode(),
        ContentType="text/csv",
    )
    send(event, context, "SUCCESS", {"Key": "sample-sales-data.csv"})
