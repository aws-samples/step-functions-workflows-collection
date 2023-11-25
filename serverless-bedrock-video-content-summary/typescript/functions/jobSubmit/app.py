import json
import os
from urllib.parse import urlparse
import uuid
import boto3

region = os.environ['AWS_DEFAULT_REGION']
queue = os.environ['CONVERT_QUEUE']
media_conver = boto3.client('mediaconvert', region_name=region)
endpoints = media_conver.describe_endpoints()
client = boto3.client('mediaconvert', region_name=region, endpoint_url=endpoints['Endpoints'][0]['Url'], verify=False)

def lambda_handler(event, context):
    # event.Records[0].s3.
    source_s3_bucket = event['sourceS3Bucket']
    source_s3_key = event['sourceS3Key']
    source_s3 = event['sourceS3']

    video_name = source_s3_key
    invocation_id = str()
    result_list = []
    result_code = 'Succeeded'
    result_string = 'The input video object was converted successfully.'
    asset_obj_arn = []
    video_id = str()

    # The type of output group determines which media players can play 
    # the files transcoded by MediaConvert.
    # For more information, see Creating outputs with AWS Elemental MediaConvert.
    output_group_type_dict = {
        'HLS_GROUP_SETTINGS': 'HlsGroupSettings',
        'FILE_GROUP_SETTINGS': 'FileGroupSettings',
        'CMAF_GROUP_SETTINGS': 'CmafGroupSettings',
        'DASH_ISO_GROUP_SETTINGS': 'DashIsoGroupSettings',
        'MS_SMOOTH_GROUP_SETTINGS': 'MsSmoothGroupSettings'
    }

    try:
        job_name = 'Default'
        with open('job.json') as file:
            job_settings = json.load(file)

        job_settings['Inputs'][0]['FileInput'] = source_s3

        # The path of each output video is constructed based on the values of 
        # the attributes in each object of OutputGroups in the job.json file. 
        destination_s3 = 's3://{0}/{1}/{2}/' \
            .format(os.environ['DEST_BUCKET'],
                    os.path.splitext(os.path.basename(source_s3_key))[0],
                    os.path.splitext(os.path.basename(job_name))[0])
        for output_group in job_settings['OutputGroups']:
            output_group_type = output_group['OutputGroupSettings']['Type']
            if output_group_type in output_group_type_dict.keys():
                output_group_type = output_group_type_dict[output_group_type]
                output_group['OutputGroupSettings'][output_group_type]['Destination'] = \
                    '{0}{1}'.format(destination_s3,str(uuid.uuid4()))
            else:
                raise ValueError('Exception: Unknown Output Group Type {}.'
                                 .format(output_group_type))
            
        job_metadata_dict = {
            'assetID': str(uuid.uuid4()),
            # 'application': os.environ['Application'],
            'input': source_s3,
            'settings': job_name
        }

        try:
            response = client.create_job(
                Role=os.environ['MEDIA_CONVERT_ROLE'], 
                Tags=job_metadata_dict, 
                Settings=job_settings,
                Queue=queue
            )
            invocation_id = response['Job']['Id']
            video_id = (response['Job']['Settings']['OutputGroups'][0]['OutputGroupSettings']['FileGroupSettings']['Destination'].split('/'))[-1]
            for output_group in job_settings['OutputGroups']:
                output_group_type = output_group['OutputGroupSettings']['Type']
                if output_group_type in output_group_type_dict.keys():
                    output_group_type = output_group_type_dict[output_group_type]
                    asset_obj_name = (output_group['OutputGroupSettings'][output_group_type]['Destination'])
                    asset_obj_arn.append(asset_obj_name.replace('s3://','arn:aws:s3:::')+'.m3u8')
            print(response)
        except Exception as error:
            result_code = 'TemporaryFailure'
            print(error)
            raise
    
    except Exception as error:
        if result_code != 'TemporaryFailure':
            result_code = 'PermanentFailure'


    finally:
        result_list.append({
            # 'taskId': task_id,
            'resultCode': result_code,
            'resultString': result_string,
            'videoName': video_name
        })

    return {
        'video_id': video_id,
        'invocation_id': invocation_id,
        'results': result_list,
        'asset_obj_arn': asset_obj_arn,
        'source_s3_bucket': source_s3_bucket,
        'source_s3_key': source_s3_key,
        'source_s3':source_s3
    }                 
   