#!/bin/bash
set -e

# Colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Vectorization Pipeline Functionality Test${NC}"

# Default values
STACK_NAME="vectorization-pipeline"
REGION=""
TEST_DOC="test-documents/test-content.txt"

# Parse command line arguments
while [[ ${#} -gt 0 ]]; do
  key="${1}"
  case ${key} in
    --region|-r)
      REGION="${2}"
      shift 2
      ;;
    --stack-name|-s)
      STACK_NAME="${2}"
      shift 2
      ;;
    --document|-d)
      TEST_DOC="${2}"
      shift 2
      ;;
    *)
      echo -e "${RED}Unknown option: ${1}${NC}"
      echo -e "Usage: ${0} [--region|-r REGION] [--stack-name|-s STACK_NAME] [--document|-d FILE_PATH]"
      exit 1
      ;;
  esac
done

# If region is still not set, try to get it from AWS config or use a default
if [ -z "${REGION}" ]; then
  REGION="$(aws configure get region)"
  if [ -z "${REGION}" ]; then
    echo -e "${YELLOW}No region specified, using default: us-west-2${NC}"
    REGION="us-west-2"
  fi
fi

# Make sure we're in the correct directory
cd "$(dirname "$0")"  # Move to the script's directory

echo -e "${YELLOW}Testing functionality for stack $STACK_NAME in $REGION${NC}"

# Step 1: Get S3 bucket name from stack outputs
echo -e "${YELLOW}Step 1: Getting S3 bucket name from stack outputs...${NC}"
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ContentBucketName`].OutputValue' --output text)

if [ -z "$BUCKET_NAME" ]; then
  echo -e "${RED}Failed to retrieve S3 bucket name from stack outputs.${NC}"
  echo -e "${YELLOW}Make sure the stack has been deployed successfully and has an output named 'ContentBucketName'.${NC}"
  exit 1
fi

echo -e "${GREEN}Found S3 bucket: $BUCKET_NAME${NC}"

# Step 2: Upload test document to S3 bucket
echo -e "${YELLOW}Step 2: Uploading test document to S3 bucket...${NC}"

if [ ! -f "$TEST_DOC" ]; then
  echo -e "${RED}Test document not found: $TEST_DOC${NC}"
  exit 1
fi

# Extract filename from path
FILENAME=$(basename "$TEST_DOC")

# Upload to raw/ prefix
aws s3 cp "$TEST_DOC" "s3://$BUCKET_NAME/raw/$FILENAME" --region $REGION

if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to upload document to S3.${NC}"
  exit 1
fi

echo -e "${GREEN}Test document uploaded successfully to s3://$BUCKET_NAME/raw/$FILENAME${NC}"

# Step 3: Wait for document processing (5 minutes max)
echo -e "${YELLOW}Step 3: Waiting for document processing...${NC}"
echo -e "${YELLOW}This may take several minutes depending on the document size and processing queue.${NC}"
echo -e "${YELLOW}Let's check the database for vectors every 30 seconds for up to 5 minutes...${NC}"

# Get database credentials from Secrets Manager
echo -e "${YELLOW}Retrieving database credentials...${NC}"
SECRET_ID="${STACK_NAME}-db-password"
SECRET_ARN=$(aws secretsmanager describe-secret --secret-id $SECRET_ID --region $REGION --query "ARN" --output text)
DB_CREDS=$(aws secretsmanager get-secret-value --secret-id "$SECRET_ARN" --region $REGION --query SecretString --output text)
DB_USERNAME=$(echo $DB_CREDS | jq -r '.username')
DB_PASSWORD=$(echo $DB_CREDS | jq -r '.password')
DB_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='DBClusterEndpoint'].OutputValue" --output text)
DB_NAME="mydb"

# Create a Python script for checking vectors
echo -e "${YELLOW}Creating database query script...${NC}"
TMP_SCRIPT=$(mktemp)
cat > "$TMP_SCRIPT" << 'EOF'
import boto3
import sys
import time
import json
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', required=True)
    parser.add_argument('--cluster-arn', required=True)
    parser.add_argument('--secret-arn', required=True)
    parser.add_argument('--filename', required=True)
    return parser.parse_args()

def main():
    args = parse_args()
    region = args.region
    cluster_arn = args.cluster_arn
    secret_arn = args.secret_arn
    filename = args.filename
    
    # Initialize clients
    rds_data = boto3.client('rds-data', region_name=region)
    
    # Query to check for vectors for this document
    query = """
    SELECT COUNT(*) as count, MIN(created_at) as first_vector
    FROM vectortable 
    WHERE path LIKE '%{}%'
    """.format(filename)
    
    response = rds_data.execute_statement(
        resourceArn=cluster_arn,
        secretArn=secret_arn,
        database="mydb",
        sql=query
    )
    
    # Process results
    records = response['records']
    if records and len(records) > 0:
        count = int(records[0][0]['longValue']) if 'longValue' in records[0][0] else 0
        
        if count > 0:
            first_vector = records[0][1]['stringValue'] if 'stringValue' in records[0][1] else "Unknown"
            print(json.dumps({"found": True, "count": count, "first_vector": first_vector}))
            return 0
        else:
            print(json.dumps({"found": False, "count": 0}))
            return 1
    
    print(json.dumps({"found": False, "error": "No records returned"}))
    return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

# Get cluster ARN
echo -e "${YELLOW}Getting database cluster ARN...${NC}"
CLUSTER_ARN=$(aws rds describe-db-clusters --db-cluster-identifier "${STACK_NAME}-db" --region $REGION --query "DBClusters[0].DBClusterArn" --output text)

echo -e "${GREEN}Database Endpoint: $DB_ENDPOINT${NC}"
echo -e "${GREEN}Cluster ARN: $CLUSTER_ARN${NC}"

# Check for vectors every 30 seconds
MAX_ATTEMPTS=10
for (( i=1; i<=MAX_ATTEMPTS; i++ )); do
    echo -e "${YELLOW}Checking for vectors (attempt $i/$MAX_ATTEMPTS)...${NC}"
    
    # Run the Python script to check for vectors
    RESULT=$(python3 $TMP_SCRIPT --region $REGION --cluster-arn "$CLUSTER_ARN" --secret-arn "$SECRET_ARN" --filename "$FILENAME")
    
    # Parse the JSON result
    FOUND=$(echo $RESULT | jq -r '.found')
    
    if [ "$FOUND" == "true" ]; then
        COUNT=$(echo $RESULT | jq -r '.count')
        FIRST_VECTOR=$(echo $RESULT | jq -r '.first_vector')
        echo -e "${GREEN}Success! Found $COUNT vector(s) in the database.${NC}"
        echo -e "${GREEN}First vector created at: $FIRST_VECTOR${NC}"
        
        # Clean up
        rm $TMP_SCRIPT
        
        echo -e "${GREEN}✅ Test completed successfully!${NC}"
        echo -e "${GREEN}The document has been processed and vectorized.${NC}"
        exit 0
    else
        echo -e "${YELLOW}No vectors found yet. Waiting 30 seconds...${NC}"
        sleep 30
    fi
    
    if [ $i -eq $MAX_ATTEMPTS ]; then
        echo -e "${RED}❌ Test failed: No vectors found after ${MAX_ATTEMPTS} attempts.${NC}"
        echo -e "${YELLOW}Possible issues:${NC}"
        echo -e "${YELLOW}- Document processing pipeline might not be working correctly${NC}"
        echo -e "${YELLOW}- The Step Functions workflow might have failed${NC}"
        echo -e "${YELLOW}- Check CloudWatch logs for errors in the Lambda functions${NC}"
        
        # Clean up
        rm $TMP_SCRIPT
        
        exit 1
    fi
done

# Clean up
rm $TMP_SCRIPT
