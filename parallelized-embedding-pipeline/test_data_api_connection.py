#!/usr/bin/env python3
import boto3
import json
import argparse
import sys
import time

def parse_args():
    parser = argparse.ArgumentParser(description="Test AWS RDS Data API connection")
    parser.add_argument("--region", "-r", default="us-west-2", help="AWS Region")
    parser.add_argument("--stack-name", "-s", default="vectorization-pipeline", help="CloudFormation stack name")
    return parser.parse_args()

def main():
    args = parse_args()
    region = args.region
    stack_name = args.stack_name

    print(f"\033[33mTesting Data API connection in {region} for stack {stack_name}...\033[0m")

    # Initialize clients
    cfn = boto3.client('cloudformation', region_name=region)
    rds_data = boto3.client('rds-data', region_name=region)
    secretsmanager = boto3.client('secretsmanager', region_name=region)
    rds = boto3.client('rds', region_name=region)

    try:
        # Get the database cluster ARN and secret ARN from CloudFormation outputs or directly
        print(f"\033[33mRetrieving database resources information...\033[0m")
        
        # Get the DB cluster identifier
        db_cluster_id = f"{stack_name}-db"
        print(f"\033[33mDB Cluster ID: {db_cluster_id}\033[0m")
        
        # Get the cluster ARN
        try:
            response = rds.describe_db_clusters(DBClusterIdentifier=db_cluster_id)
            cluster_arn = response['DBClusters'][0]['DBClusterArn']
            engine = response['DBClusters'][0]['Engine']
            status = response['DBClusters'][0]['Status']
            port = response['DBClusters'][0]['Port']
            
            print(f"\033[32mCluster ARN: {cluster_arn}\033[0m")
            print(f"\033[32mEngine: {engine}\033[0m")
            print(f"\033[32mStatus: {status}\033[0m")
            print(f"\033[32mPort: {port}\033[0m")
        except Exception as e:
            print(f"\033[31mError getting cluster information: {str(e)}\033[0m")
            return False

        # Get the secret ARN
        secret_id = f"{stack_name}-db-password"
        try:
            response = secretsmanager.describe_secret(SecretId=secret_id)
            secret_arn = response['ARN']
            print(f"\033[32mSecret ARN: {secret_arn}\033[0m")
        except Exception as e:
            print(f"\033[31mError getting secret ARN: {str(e)}\033[0m")
            return False

        # Database name
        database_name = 'mydb'
        print(f"\033[33mUsing database name: {database_name}\033[0m")

        # Test connection with retries
        print(f"\033[33mTesting database connection via Data API...\033[0m")
        max_retries = 3
        success = False

        for attempt in range(max_retries):
            try:
                print(f"\033[33mAttempt {attempt+1}/{max_retries}...\033[0m")
                
                # Execute a simple SQL statement
                response = rds_data.execute_statement(
                    resourceArn=cluster_arn,
                    secretArn=secret_arn, 
                    database=database_name,
                    sql="SELECT current_timestamp as time, current_user as user, version() as version"
                )
                
                # Process results
                records = response['records']
                if records and len(records) > 0:
                    time_val = records[0][0]['stringValue'] if 'stringValue' in records[0][0] else "Unknown"
                    user_val = records[0][1]['stringValue'] if 'stringValue' in records[0][1] else "Unknown"
                    version_val = records[0][2]['stringValue'] if 'stringValue' in records[0][2] else "Unknown"
                    
                    print(f"\033[32m✓ Connection successful!\033[0m")
                    print(f"\033[32m  Current time: {time_val}\033[0m")
                    print(f"\033[32m  Connected as: {user_val}\033[0m")
                    print(f"\033[32m  Database version: {version_val}\033[0m")
                    
                    # Test creating the pgvector extension
                    print(f"\033[33mTesting pgvector extension installation...\033[0m")
                    try:
                        response = rds_data.execute_statement(
                            resourceArn=cluster_arn,
                            secretArn=secret_arn,
                            database=database_name,
                            sql="CREATE EXTENSION IF NOT EXISTS vector"
                        )
                        print(f"\033[32m✓ Successfully created pgvector extension!\033[0m")
                    except Exception as e:
                        print(f"\033[31m✗ Error creating pgvector extension: {str(e)}\033[0m")
                    
                    success = True
                    break
                else:
                    print(f"\033[31m✗ No records returned from query\033[0m")
                    
            except Exception as e:
                error_message = str(e)
                print(f"\033[31m✗ Connection failed: {error_message}\033[0m")
                
                if "communications link failure" in error_message.lower() or "network" in error_message.lower():
                    print(f"\033[33m  Network connectivity issue detected\033[0m")
                elif "access denied" in error_message.lower() or "permission" in error_message.lower():
                    print(f"\033[33m  Permissions/authentication issue detected\033[0m")
                elif "does not exist" in error_message.lower():
                    print(f"\033[33m  Database '{database_name}' does not exist or is not ready\033[0m")
                    
                if attempt < max_retries - 1:
                    wait_time = 5 * (2 ** attempt)  # exponential backoff: 5, 10, 20 seconds
                    print(f"\033[33m  Waiting {wait_time} seconds before next attempt...\033[0m")
                    time.sleep(wait_time)

        if not success:
            print(f"\033[31m✗ All {max_retries} connection attempts failed.\033[0m")
            print(f"\033[33mTroubleshooting suggestions:\033[0m")
            print(f"\033[33m1. Check that the database cluster status is 'available'\033[0m")
            print(f"\033[33m2. Verify that Security Group rules allow access from Lambda to port {port}\033[0m")
            print(f"\033[33m3. Ensure that the database name '{database_name}' exists\033[0m")
            print(f"\033[33m4. Check that the secrets in Secrets Manager have correct credentials\033[0m")
            return False

        return success

    except Exception as e:
        print(f"\033[31mError: {str(e)}\033[0m")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
