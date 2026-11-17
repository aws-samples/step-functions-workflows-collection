"""
RSS Ingestion Lambda
Polls AWS What's New RSS feed, deduplicates against DynamoDB,
matches announcements to workload profiles by service keywords,
and triggers Step Functions for matched announcements.
"""
import boto3
import json
import os
import defusedxml.ElementTree as ET
import urllib.request
import urllib.parse
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
sfn_client = boto3.client('stepfunctions')

STATE_TABLE = os.environ.get('STATE_TABLE', 'FeatureRelevanceState')
PROFILES_TABLE = os.environ.get('PROFILES_TABLE', 'WorkloadProfiles')
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN', '')
RSS_URL = 'https://aws.amazon.com/about-aws/whats-new/recent/feed/'

# Map AWS service names to keywords for matching
SERVICE_KEYWORDS = {
    'Amazon EC2': ['ec2', 'elastic compute', 'instances'],
    'Amazon S3': ['s3', 'simple storage', 'object storage'],
    'Amazon RDS': ['rds', 'relational database', 'aurora'],
    'Amazon Aurora': ['aurora'],
    'AWS Lambda': ['lambda', 'serverless function'],
    'Amazon DynamoDB': ['dynamodb', 'nosql'],
    'Amazon EKS': ['eks', 'kubernetes', 'k8s'],
    'Amazon ECS': ['ecs', 'container service'],
    'AWS Fargate': ['fargate'],
    'Amazon CloudFront': ['cloudfront', 'cdn', 'content delivery'],
    'Amazon Kinesis': ['kinesis', 'streaming', 'data streams'],
    'Amazon Redshift': ['redshift', 'data warehouse'],
    'AWS Glue': ['glue', 'etl', 'data catalog'],
    'Amazon SageMaker': ['sagemaker', 'machine learning', 'ml'],
    'AWS Step Functions': ['step functions', 'state machine', 'workflow'],
    'Amazon SQS': ['sqs', 'simple queue'],
    'Amazon SNS': ['sns', 'simple notification'],
    'AWS KMS': ['kms', 'key management', 'encryption'],
    'Amazon VPC': ['vpc', 'virtual private cloud', 'networking'],
    'AWS PrivateLink': ['privatelink', 'vpc endpoint'],
    'Amazon ECR': ['ecr', 'container registry'],
    'AWS Elemental MediaConvert': ['mediaconvert', 'video processing'],
    'Amazon OpenSearch': ['opensearch', 'elasticsearch'],
    'Amazon Bedrock': ['bedrock', 'foundation model'],
}


def lambda_handler(event, context):
    """Main handler - polls RSS and processes new announcements."""
    state_table = dynamodb.Table(STATE_TABLE)
    profiles_table = dynamodb.Table(PROFILES_TABLE)

    # Support test mode with a pre-built announcement
    if event.get('test_mode'):
        return process_test_announcement(event, state_table, profiles_table)

    # Fetch and parse RSS feed
    try:
        # Validate URL scheme before opening
        parsed_url = urllib.parse.urlparse(RSS_URL)
        if parsed_url.scheme not in ('https', 'http'):
            raise ValueError(f"Invalid URL scheme: {parsed_url.scheme}")
        req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'AWSFeatureRelevance/1.0'})
        response = urllib.request.urlopen(req, timeout=30)  # nosec B310
        xml_content = response.read()
        root = ET.fromstring(xml_content)
    except Exception as e:
        print(f"ERROR: Failed to fetch RSS feed: {e}")
        return {'statusCode': 500, 'error': str(e)}

    # Get all workload profiles
    profiles = get_all_profiles(profiles_table)
    if not profiles:
        print("WARNING: No workload profiles found. Skipping processing.")
        return {'statusCode': 200, 'announcements_processed': 0, 'reason': 'no_profiles'}

    # Process each RSS item
    processed = 0
    skipped_duplicate = 0
    skipped_no_match = 0

    for item in root.findall('.//item'):
        title = item.find('title').text or ''
        link = item.find('link').text or ''
        description = item.find('description').text or ''
        pub_date = item.find('pubDate').text or ''
        categories = [c.text for c in item.findall('category') if c.text]

        # Deduplication check
        if is_already_processed(state_table, link):
            skipped_duplicate += 1
            continue

        # Match announcement against workload profiles
        matched_profiles = match_announcement_to_profiles(
            title, description, categories, profiles
        )

        if not matched_profiles:
            skipped_no_match += 1
            # Still mark as processed to avoid re-checking
            mark_processed(state_table, link, title, matched=False)
            continue

        # Build announcement payload
        announcement = {
            'title': title,
            'link': link,
            'description': description,
            'pub_date': pub_date,
            'categories': categories,
            'matched_profiles': matched_profiles,
            'ingested_at': datetime.now(timezone.utc).isoformat()
        }

        # Trigger Step Functions for each matched profile
        for profile_match in matched_profiles:
            execution_input = {
                'announcement': announcement,
                'workload': profile_match
            }
            try:
                sfn_client.start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    name=f"{profile_match['workload_id']}-{int(datetime.now(timezone.utc).timestamp())}",
                    input=json.dumps(execution_input, default=str)
                )
                print(f"Started execution for: {title[:60]}... → {profile_match['workload_name']}")
            except Exception as e:
                print(f"ERROR starting execution: {e}")

        # Mark as processed
        mark_processed(state_table, link, title, matched=True)
        processed += 1

    result = {
        'statusCode': 200,
        'announcements_processed': processed,
        'skipped_duplicate': skipped_duplicate,
        'skipped_no_match': skipped_no_match,
        'total_profiles': len(profiles)
    }
    print(f"Result: {json.dumps(result)}")
    return result


def process_test_announcement(event, state_table, profiles_table):
    """Process a test announcement (for demo purposes)."""
    profiles = get_all_profiles(profiles_table)

    # Use provided test announcement or a default
    test_announcement = event.get('announcement', {
        'title': 'Amazon EKS announces Graviton4 support for managed node groups',
        'link': 'https://aws.amazon.com/about-aws/whats-new/2026/07/eks-graviton4-managed-node-groups/',
        'description': 'Amazon Elastic Kubernetes Service (EKS) now supports Graviton4-based instances (r8g, m8g, c8g) in managed node groups. Graviton4 delivers up to 30% better price-performance compared to Graviton3 for containerized workloads, with enhanced memory bandwidth for data-intensive applications.',
        'pub_date': datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT'),
        'categories': ['Amazon Elastic Kubernetes Service', 'Compute'],
        'ingested_at': datetime.now(timezone.utc).isoformat()
    })

    matched_profiles = match_announcement_to_profiles(
        test_announcement['title'],
        test_announcement['description'],
        test_announcement.get('categories', []),
        profiles
    )

    if not matched_profiles:
        # Force match to first profile for testing
        if profiles:
            matched_profiles = [profiles[0]]

    test_announcement['matched_profiles'] = matched_profiles

    # Trigger Step Functions
    for profile_match in matched_profiles:
        execution_input = {
            'announcement': test_announcement,
            'workload': profile_match
        }
        sfn_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"test-{profile_match['workload_id']}-{int(datetime.now(timezone.utc).timestamp())}",
            input=json.dumps(execution_input, default=str)
        )

    return {
        'statusCode': 200,
        'test_mode': True,
        'matched_profiles': len(matched_profiles),
        'announcement_title': test_announcement['title']
    }


def get_all_profiles(table):
    """Retrieve all workload profiles from DynamoDB."""
    profiles = []
    response = table.scan()
    profiles.extend(response.get('Items', []))
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        profiles.extend(response.get('Items', []))
    return profiles


def match_announcement_to_profiles(title, description, categories, profiles):
    """Match an announcement against workload profiles by service keywords."""
    text_lower = f"{title} {description} {' '.join(categories)}".lower()
    matched = []

    for profile in profiles:
        key_services = profile.get('key_services', [])
        if isinstance(key_services, str):
            key_services = json.loads(key_services)

        for service in key_services:
            keywords = SERVICE_KEYWORDS.get(service, [service.lower().replace('amazon ', '').replace('aws ', '')])
            if any(kw.lower() in text_lower for kw in keywords):
                matched.append({
                    'workload_id': profile['workload_id'],
                    'workload_name': profile.get('workload_name', ''),
                    'matched_service': service,
                    'workload_tier': profile.get('workload_tier', 'standard'),
                    'pod_slack_channel': profile.get('pod_slack_channel', '#aws-notifications'),
                    'free_text_description': profile.get('free_text_description', ''),
                    'key_services': key_services,
                    'account_ids': profile.get('account_ids', [])
                })
                break  # One match per profile is enough

    return matched


def is_already_processed(table, url):
    """Check if this announcement URL has already been processed."""
    try:
        response = table.get_item(Key={'announcement_url': url})
        return 'Item' in response
    except Exception:
        return False


def mark_processed(table, url, title, matched):
    """Mark an announcement as processed in the state table."""
    table.put_item(Item={
        'announcement_url': url,
        'title': title,
        'matched': matched,
        'processed_at': datetime.now(timezone.utc).isoformat(),
        'ttl': int(datetime.now(timezone.utc).timestamp()) + (30 * 86400)  # 30 day TTL
    })
