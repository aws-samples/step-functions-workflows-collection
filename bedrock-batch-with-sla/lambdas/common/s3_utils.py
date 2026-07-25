import json


def parse_s3_uri(uri):
    parts = uri.replace('s3://', '').split('/', 1)
    return parts[0], parts[1] if len(parts) > 1 else ''


def read_json_from_s3(s3, bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(response['Body'].read().decode('utf-8'))


def read_jsonl_from_s3(s3, bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')
    return [json.loads(line) for line in content.strip().split('\n') if line]


def write_jsonl_to_s3(s3, bucket, key, records):
    content = '\n'.join(json.dumps(rec) for rec in records)
    s3.put_object(Bucket=bucket, Key=key, Body=content.encode('utf-8'))
