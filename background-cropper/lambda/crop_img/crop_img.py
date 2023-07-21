import boto3
import io
import json
import os
import PIL
from PIL import Image
from io import BytesIO

out_bucket = os.environ['DESTINATION_BUCKET']
#crop image using BoundingBox of Person object identified by Rekognition labels
def crop_picture(bucket, fname, labels):

    s3 = boto3.resource('s3')
    in_mem_file = BytesIO()
 
    #get original image
    bucket = s3.Bucket(bucket)
    file_byte_string = bucket.Object(fname).get().get('Body').read()
    img = Image.open(BytesIO(file_byte_string))
    img_format = img.format
    img_width, img_height = img.size

    #if labels is a str, error happened in detecting labels, 
    #so store original imgage to destination S3
    if isinstance(labels, str):
        pass
    else:
        for label in labels:
            if (label['Name'] == 'Person'):
                for instance in label['Instances']:
                    #get BoundingBox location
                    top = img_height * instance['BoundingBox']['Top']
                    left = img_width * instance['BoundingBox']['Left']
                    width = img_width * instance['BoundingBox']['Width']
                    height = img_height * instance['BoundingBox']['Height']
                    #crop image
                    img = img.crop((left, top, left + width, top + height))
                    break
                break

    #storing image to S3
    img.save(in_mem_file, img_format)
    in_mem_file.seek(0)

    return s3.Object(out_bucket, fname).put(Body=in_mem_file)

def lambda_handler(event, context):
    bucket = event['Bucket']
    fname = event['FileName']
    labels = event['Labels']
    crop_picture(bucket=bucket, fname=fname, labels=labels)
    response = json.dumps({
        'Bucket': out_bucket,
        'FileName': fname
    })
    return json.loads(response)
