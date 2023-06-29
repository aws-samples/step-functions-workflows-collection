import boto3
import json
import os

client = boto3.client("firehose")
delivery_stream_arn = os.environ["ERROR_DELIVERY_STREAM_ARN"]

#
# def send_to_firehose(item, execution_id):
#     client.put_record(
#         DeliveryStreamName=delivery_stream_arn.split("/")[-1],
#         # replace <your-delivery-stream-name> with your actual delivery stream name
#         Record={
#             'Data': json.dumps(item).encode('utf-8')
#         }
#     )


def send(items, execution_name):
    client.put_record(
        DeliveryStreamName=delivery_stream_arn.split("/")[-1],
        Record={
            "Data": json.dumps(
                {"execution_name": execution_name, "items": items}
            ).encode("utf-8")
        },
    )
