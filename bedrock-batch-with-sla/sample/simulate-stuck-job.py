#!/usr/bin/env python3
"""
Simulation script to test the stuck job detection and fallback path.

This script helps test the CloudWatch alarm → SNS → Trigger Lambda → Fallback flow
by providing ways to simulate a stuck batch job scenario.

Usage:
    python simulate-stuck-job.py --help
"""

import argparse
import boto3
import json
import time
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(
        description='Simulate stuck Bedrock batch job scenarios for testing'
    )
    parser.add_argument(
        '--job-id',
        required=True,
        help='Job ID to monitor (from DynamoDB table)'
    )
    parser.add_argument(
        '--action',
        choices=['check-status', 'force-alarm', 'monitor'],
        default='check-status',
        help='Action to perform'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region'
    )
    parser.add_argument(
        '--table-name',
        default='bedrock-batch-sla-jobs',
        help='DynamoDB table name'
    )

    args = parser.parse_args()

    dynamodb = boto3.client('dynamodb', region_name=args.region)
    bedrock = boto3.client('bedrock', region_name=args.region)
    cloudwatch = boto3.client('cloudwatch', region_name=args.region)

    if args.action == 'check-status':
        check_job_status(dynamodb, bedrock, args.job_id, args.table_name)
    elif args.action == 'force-alarm':
        force_alarm_state(cloudwatch, args.region)
    elif args.action == 'monitor':
        monitor_job(dynamodb, bedrock, args.job_id, args.table_name)


def check_job_status(dynamodb, bedrock, job_id, table_name):
    """Check the current status of a job."""
    print(f"Checking status for job: {job_id}")

    # Get job from DynamoDB
    response = dynamodb.get_item(
        TableName=table_name,
        Key={'JobId': {'S': job_id}}
    )

    if 'Item' not in response:
        print(f"Job {job_id} not found in DynamoDB")
        return

    item = response['Item']
    print(f"\nDynamoDB Record:")
    print(f"  Status: {item.get('Status', {}).get('S', 'N/A')}")
    print(f"  CreatedAt: {item.get('CreatedAt', {}).get('S', 'N/A')}")
    print(f"  BedrockJobArn: {item.get('BedrockJobArn', {}).get('S', 'N/A')}")

    if 'BedrockJobArn' in item:
        bedrock_job_arn = item['BedrockJobArn']['S']
        job_name = bedrock_job_arn.split('/')[-1]

        try:
            job_details = bedrock.get_model_invocation_job(jobIdentifier=job_name)
            print(f"\nBedrock Batch Job:")
            print(f"  Status: {job_details.get('status', 'N/A')}")
            print(f"  Model: {job_details.get('modelId', 'N/A')}")
            print(f"  Submit Time: {job_details.get('submitTime', 'N/A')}")
            if 'inputDataConfig' in job_details:
                print(f"  Input Records: {job_details['inputDataConfig'].get('recordCount', 'N/A')}")
            if 'outputDataConfig' in job_details:
                print(f"  Processed Records: {job_details['outputDataConfig'].get('recordCount', 'N/A')}")
        except Exception as e:
            print(f"\nFailed to get Bedrock job details: {e}")


def force_alarm_state(cloudwatch, region):
    """
    Force the CloudWatch alarm into ALARM state for testing.
    Note: This doesn't actually trigger the alarm action, but sets its state.
    """
    alarm_name = 'bedrock-batch-sla-stuck-job'

    print(f"Setting alarm {alarm_name} to ALARM state...")

    try:
        cloudwatch.set_alarm_state(
            AlarmName=alarm_name,
            StateValue='ALARM',
            StateReason='Manual test trigger via simulate-stuck-job.py',
            StateReasonData=json.dumps({
                'timestamp': datetime.now().isoformat(),
                'source': 'simulate-stuck-job.py'
            })
        )
        print(f"Alarm {alarm_name} set to ALARM state")
        print("Note: This triggers the alarm actions (SNS → Lambda)")
    except Exception as e:
        print(f"Failed to set alarm state: {e}")


def monitor_job(dynamodb, bedrock, job_id, table_name, interval=30, duration=300):
    """
    Monitor a job's progress over time to detect if it's stuck.
    """
    print(f"Monitoring job {job_id} for {duration} seconds (checking every {interval}s)")
    print("Press Ctrl+C to stop\n")

    start_time = time.time()
    previous_processed = None

    try:
        while time.time() - start_time < duration:
            response = dynamodb.get_item(
                TableName=table_name,
                Key={'JobId': {'S': job_id}}
            )

            if 'Item' not in response:
                print(f"[{datetime.now().isoformat()}] Job not found")
                break

            item = response['Item']
            status = item.get('Status', {}).get('S', 'N/A')

            if 'BedrockJobArn' in item:
                bedrock_job_arn = item['BedrockJobArn']['S']
                job_name = bedrock_job_arn.split('/')[-1]

                try:
                    job_details = bedrock.get_model_invocation_job(jobIdentifier=job_name)
                    bedrock_status = job_details.get('status', 'N/A')
                    processed = job_details.get('outputDataConfig', {}).get('recordCount', 0)

                    print(f"[{datetime.now().isoformat()}] Status: {status} | Bedrock: {bedrock_status} | Processed: {processed}")

                    if previous_processed is not None and processed == previous_processed:
                        print("  ⚠️  No progress detected")
                    elif previous_processed is not None:
                        print(f"  ✓ Progress: +{processed - previous_processed} records")

                    previous_processed = processed

                except Exception as e:
                    print(f"[{datetime.now().isoformat()}] Failed to get job details: {e}")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")


if __name__ == '__main__':
    main()
