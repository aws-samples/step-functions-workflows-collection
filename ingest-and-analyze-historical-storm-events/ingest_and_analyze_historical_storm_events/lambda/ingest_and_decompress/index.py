import gzip
import shutil
import logging
import os
import boto3
import glob

logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3 = boto3.resource('s3')
s3client = boto3.client('s3')

output_file = "output.tar.gz"

STORM_EVENT_FATALITIES = "fatalities"
STORM_EVENT_DETAILS = "details"
STORM_EVENT_LOCATIONS = "locations"
STORM_EVENT_OTHERS = "others"


def fetch_source(bucket_name, key):
    file_name = parse_naked_file_name(key)
    temp_file = f"/tmp/{file_name}"
    source_bucket = s3.Bucket(bucket_name)
    source_bucket.download_file(key, temp_file)
    return temp_file


def split_s3_path(s3_path):
    path_parts = s3_path.replace("s3://", "").split("/")
    bucket = path_parts.pop(0)
    key = "/".join(path_parts)
    return bucket, key


def put_result(local_file, destination_bucket_name, destination_key):
    logger.info('putting file {} in to bucket: {} with file name {}'.format(local_file, destination_bucket_name,
                                                                            destination_key))
    destination_bucket = s3.Bucket(destination_bucket_name)
    destination_bucket.upload_file(local_file, destination_key)


def temp_folder():
    return '/tmp'


def clean_temp_folder():
    for file in glob.glob(temp_folder() + '/*.gz'):
        os.remove(file)


def parse_naked_file_name(raw_name):
    """
    :param raw_name:  raw_source/abs/asd/asd/StormEvents_details-ftp_v1.0_d1951_c20210803.csv.gz
    :return: StormEvents_details-ftp_v1.0_d1951_c20210803.csv.gz
    """
    keys = raw_name.split("/")
    return keys[len(keys) - 1]


def get_storm_event_file_type(file_name):
    if STORM_EVENT_DETAILS in file_name:
        return "details"
    elif STORM_EVENT_LOCATIONS in file_name:
        return STORM_EVENT_LOCATIONS
    elif STORM_EVENT_FATALITIES in file_name:
        return STORM_EVENT_FATALITIES
    else:
        return STORM_EVENT_OTHERS


def decompress(event, context):
    """
    :param event:
    {
        'Items': [{
            'Etag': '"d41d8cd98f00b204e9800998ecf8427e"',
            'Key': 'raw_source/',
            'LastModified': 1673044270.0,
            'Size': 0,
            'StorageClass': 'STANDARD'
        }, {
            'Etag': '"86c8ea2057016350b8dcb64bc731d291"',
            'Key': 'raw_source/StormEvents_details-ftp_v1.0_d1950_c20210803.csv.gz',
            'LastModified': 1673044381.0,
            'Size': 10597,
            'StorageClass': 'STANDARD'
        }, {
            'Etag': '"2cc2a70606eeb6595a094e18c2a49101"',
            'Key': 'raw_source/StormEvents_details-ftp_v1.0_d1951_c20210803.csv.gz',
            'LastModified': 1673044381.0,
            'Size': 12020,
            'StorageClass': 'STANDARD'
        }]
    }
    :param context:
    :return:
    """
    try:
        bucket_name = os.environ["raw_source_bucket"]
        items = event["Items"]
        for item in items:
            clean_temp_folder()
            key = item["Key"]
            last_char = key[len(key) - 1]
            if last_char == "/":
                continue
            gz_file_uri = fetch_source(bucket_name=bucket_name, key=key)
            gz_file_name = parse_naked_file_name(gz_file_uri)
            gz_output_name = gz_file_name.split(".gz")[0]
            storm_event_record_type = get_storm_event_file_type(gz_output_name)
            try:
                with gzip.open(f'/tmp/{gz_file_name}', "rb") as f_in, open(f'/tmp/{gz_output_name}', "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    put_result(f'/tmp/{gz_output_name}', destination_bucket_name=bucket_name,
                               destination_key=f"formatted/{storm_event_record_type}/{gz_output_name}")
            except Exception as e:
                logger.error(e)
                logger.error(f"Error decompressing the file /tmp/{gz_file_name}")

        return {
            "STATUS": "SUCCESS",
            "MESSAGE": "Files decompressed"
        }

    except Exception as e:
        logger.error(e)
        return {
            "STATUS": "FAIL",
            "MESSAGE": "Failed to decompress"
        }

