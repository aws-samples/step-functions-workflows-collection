#!/usr/bin/env python3
"""
End-to-end integration test for Bedrock Batch SLA Fallback system.

Prerequisites:
- CDK stack deployed to AWS account
- AWS credentials configured
- boto3 >= 1.35.1

Usage:
    python e2e-test.py --stack-name BedrockBatchSlaFallbackStack --region us-east-1
"""

import argparse
import boto3
import json
import time
from datetime import datetime
import sys


class E2ETest:
    def __init__(self, stack_name, region='us-east-1'):
        self.stack_name = stack_name
        self.region = region

        self.cfn = boto3.client('cloudformation', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.dynamodb = boto3.client('dynamodb', region_name=region)
        self.sfn = boto3.client('stepfunctions', region_name=region)

        self.outputs = {}
        self.load_stack_outputs()

    def load_stack_outputs(self):
        """Load stack outputs for resource identifiers"""
        print(f"Loading outputs from stack: {self.stack_name}")
        response = self.cfn.describe_stacks(StackName=self.stack_name)
        stack = response['Stacks'][0]

        for output in stack['Outputs']:
            self.outputs[output['OutputKey']] = output['OutputValue']

        print(f"  Input Bucket: {self.outputs['InputBucketName']}")
        print(f"  Output Bucket: {self.outputs['OutputBucketName']}")
        print(f"  State Machine: {self.outputs['StateMachineArn']}")
        print(f"  Jobs Table: {self.outputs['JobsTableName']}")
        print()

    def test_happy_path(self):
        """Test happy path: upload input, batch completes successfully"""
        print("=" * 70)
        print("TEST 1: Happy Path - Batch Completion")
        print("=" * 70)

        # Upload sample input
        input_bucket = self.outputs['InputBucketName']
        test_key = f"test-input-{int(time.time())}.jsonl"

        print(f"1. Uploading test input to s3://{input_bucket}/{test_key}")
        with open('../../sample/input.jsonl', 'r') as f:
            self.s3.put_object(
                Bucket=input_bucket,
                Key=test_key,
                Body=f.read()
            )

        print("2. Waiting for Registrar Lambda to process (5s)...")
        time.sleep(5)

        # Check DynamoDB for job creation
        print("3. Checking DynamoDB for job record...")
        table_name = self.outputs['JobsTableName']
        response = self.dynamodb.scan(
            TableName=table_name,
            Limit=1,
            ScanIndexForward=False
        )

        if response['Items']:
            job_id = response['Items'][0]['JobId']['S']
            print(f"   ✓ Job created: {job_id}")
        else:
            print("   ✗ No job found in DynamoDB")
            return False

        # Monitor Step Functions execution
        print("4. Monitoring Step Functions execution...")
        state_machine_arn = self.outputs['StateMachineArn']

        # List recent executions
        executions = self.sfn.list_executions(
            stateMachineArn=state_machine_arn,
            statusFilter='RUNNING',
            maxResults=1
        )

        if executions['executions']:
            execution_arn = executions['executions'][0]['executionArn']
            print(f"   Execution ARN: {execution_arn}")
            print("   Note: Batch jobs can take hours - monitor in AWS Console")
            return True
        else:
            print("   ✗ No running executions found")
            return False

    def test_fallback_timeout(self):
        """Test fallback path by forcing timeout (requires redeployment with short timeout)"""
        print("\n" + "=" * 70)
        print("TEST 2: Fallback Path - Timeout")
        print("=" * 70)
        print("To test this scenario:")
        print("1. Redeploy with very short BATCH_CUTOFF (e.g., 60 seconds)")
        print("   cdk deploy -c slaTotalMinutes=2")
        print("2. Upload input and verify timeout triggers fallback")
        print("3. Check that Distributed Map runs and Merge completes")
        print()
        return True

    def test_alarm_fallback(self):
        """Test alarm-triggered fallback"""
        print("=" * 70)
        print("TEST 3: Stuck Job Alarm")
        print("=" * 70)
        print("To test this scenario:")
        print("1. Start a batch job")
        print("2. Use sample/simulate-stuck-job.py to force alarm state")
        print("3. Verify Trigger Lambda resumes state machine")
        print()
        return True

    def verify_outputs(self, job_id):
        """Verify merged output has correct structure"""
        print("=" * 70)
        print("VERIFICATION: Output Structure")
        print("=" * 70)

        output_bucket = self.outputs['OutputBucketName']
        merged_key = f"merged-output/{job_id}/results.jsonl"

        try:
            response = self.s3.get_object(Bucket=output_bucket, Key=merged_key)
            content = response['Body'].read().decode('utf-8')
            records = [json.loads(line) for line in content.strip().split('\n')]

            print(f"  ✓ Merged output found: {len(records)} records")

            # Check for recordId uniqueness
            record_ids = [r['recordId'] for r in records if 'recordId' in r]
            if len(record_ids) == len(set(record_ids)):
                print("  ✓ All recordIds are unique")
            else:
                print("  ✗ Duplicate recordIds found")
                return False

            # Check for required fields
            for i, rec in enumerate(records[:3]):
                print(f"  Sample record {i+1}: {rec.keys()}")

            return True

        except Exception as e:
            print(f"  ✗ Failed to read merged output: {e}")
            return False

    def cleanup(self):
        """Optional cleanup of test resources"""
        print("\n" + "=" * 70)
        print("CLEANUP")
        print("=" * 70)
        print("To clean up test resources:")
        print(f"  aws s3 rm s3://{self.outputs['InputBucketName']}/ --recursive")
        print(f"  aws s3 rm s3://{self.outputs['OutputBucketName']}/ --recursive")
        print(f"  cdk destroy {self.stack_name}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='End-to-end integration test for Bedrock Batch SLA Fallback'
    )
    parser.add_argument(
        '--stack-name',
        default='BedrockBatchSlaFallbackStack',
        help='CloudFormation stack name'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region'
    )
    parser.add_argument(
        '--test',
        choices=['all', 'happy-path', 'fallback', 'alarm'],
        default='all',
        help='Which test to run'
    )

    args = parser.parse_args()

    try:
        tester = E2ETest(args.stack_name, args.region)

        if args.test in ['all', 'happy-path']:
            success = tester.test_happy_path()
            if not success:
                print("\n✗ Happy path test failed")
                sys.exit(1)

        if args.test in ['all', 'fallback']:
            tester.test_fallback_timeout()

        if args.test in ['all', 'alarm']:
            tester.test_alarm_fallback()

        tester.cleanup()

        print("\n" + "=" * 70)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 70)
        print("✓ Basic workflow initiated successfully")
        print("  Monitor execution in AWS Step Functions Console")
        print("  Use sample/simulate-stuck-job.py for alarm testing")
        print()

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
