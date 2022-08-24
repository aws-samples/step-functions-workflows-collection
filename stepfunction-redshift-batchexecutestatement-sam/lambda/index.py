import json, boto3, urllib3, os

http = urllib3.PoolManager()
s3=boto3.resource('s3')

def lambda_handler(event, context):
    # TODO implement
    resp = {}
    print (event)
    BUCKET = event['ResourceProperties']['S3Bucket']
    if event['RequestType'] == 'Delete':
        try:
            bucket = s3.Bucket(BUCKET)
            bucket.delete_objects(Delete={
                	'Objects': [
                    {
                        'Key': "*"   # the_name of_your_file
                    }
                ]
            })
            try:
                bucket.object_versions.delete()
            except Exception as e:
                print ("error in deleting version:", e)
            print("deletion complete")
        except Exception as e:
            print ("error:", e)
        data = {"output":"Delete event."}
    if event['RequestType'] == 'Create':
        s3.meta.client.upload_file('newdata.csv', BUCKET, 'newdata.csv')
        data = {"output":"Create event."}
    responseBody =  {
        'Status': "SUCCESS",
        "PhysicalResourceId":"customresource",
        "StackId":event['StackId'],
        "RequestId":event['RequestId'],
        "LogicalResourceId":event['LogicalResourceId'],
        "Data":data
    }
    json_responseBody = json.dumps(responseBody)
    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }
    response = http.request('PUT', event['ResponseURL'], headers=headers, body=json_responseBody)