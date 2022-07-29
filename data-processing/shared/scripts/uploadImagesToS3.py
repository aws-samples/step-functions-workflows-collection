###########################################################################
# Pre-requisite: Create AWS resources using SAM in this lab
#
# - Retrieves Bucket Name from S3 created from this lab
# - Updates the statemchine/input.json files with the correct bucket name
# - Uploads all images under resources folder to bucket
#
# Run this script from the data-processing root folder
###########################################################################
import os
import glob
import boto3

# Retrieves the bucket name based on the convention used when creating it through SAM deploy
def get_bucket_name(client):
    bucket_name = ""
    bucket_name_to_match = "data-workflow-pattern-"
    
    bucket_list = client.list_buckets()
    for bucket_item in bucket_list['Buckets']:
        bucket_item_name = bucket_item['Name']
        if bucket_name_to_match in bucket_item_name:
            bucket_name = bucket_item_name
    
    return bucket_name

# updates the bucket name parameter in the input file for the state machine for testing
def update_bucket_name_input(bucket_name):
    # update parameter input file with correct bucket name
    input_file_name = "../sam/statemachine/input.json"
    output_file_name = "output/" + bucket_name + "-input.json"

    read_file = open(input_file_name, "rt")
    file_contents = read_file.read()
    updated_contents = file_contents.replace('mybucketname', bucket_name)
    read_file.close()

    write_updates = open(output_file_name, "wt")
    write_updates.write(updated_contents)
    write_updates.close()

# uploads test images to the bucket created during the SAM deploy
def upload_files(client, bucket_name):
    # upload all files under the images folder
    files = glob.glob('images/*')
    for file in files:
        key = file.replace("images/", "").strip()
        client.upload_file(file, bucket_name, key)


# get AWS client, obtain the correct bucket name, update the input file with the correct bucket name and upload images to the bucket
client = boto3.client('s3')
bucket_name = get_bucket_name(client)
update_bucket_name_input(bucket_name)
upload_files(client, bucket_name)


