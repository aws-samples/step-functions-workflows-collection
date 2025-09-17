#!/bin/bash
set -e

# Colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Direct Vectorization Function Test${NC}"

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

echo -e "${YELLOW}Testing VectorizeFunction directly for stack $STACK_NAME in $REGION${NC}"

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
DEST_KEY="cleaned/${FILENAME}_text.txt"

# Upload to cleaned/ prefix directly (bypass the normal ingestion process)
aws s3 cp "$TEST_DOC" "s3://$BUCKET_NAME/$DEST_KEY" --region $REGION

if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to upload document to S3.${NC}"
  exit 1
fi

echo -e "${GREEN}Test document uploaded successfully to s3://$BUCKET_NAME/$DEST_KEY${NC}"

# Step 3: Get the Lambda function name
echo -e "${YELLOW}Step 3: Getting Lambda function details...${NC}"
FUNCTION_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name $STACK_NAME \
  --logical-resource-id VectorizeFunction \
  --region $REGION \
  --query 'StackResources[0].PhysicalResourceId' \
  --output text)

echo -e "${GREEN}Found Lambda function: $FUNCTION_NAME${NC}"

# Step 4: Invoke the Lambda function directly with byte ranges
echo -e "${YELLOW}Step 4: Invoking Lambda function directly...${NC}"

# Get file size
SIZE=$(aws s3api head-object --bucket $BUCKET_NAME --key $DEST_KEY --region $REGION --query 'ContentLength' --output text)
echo -e "${GREEN}File size: $SIZE bytes${NC}"

# Create a temporary file for the Lambda payload
TMP_PAYLOAD=$(mktemp)
cat > $TMP_PAYLOAD << EOF
{
  "Bucket": "$BUCKET_NAME",
  "Key": "$DEST_KEY",
  "ByteRangeStart": 0,
  "ByteRangeEnd": $((SIZE - 1))
}
EOF

echo -e "${YELLOW}Payload:${NC}"
cat $TMP_PAYLOAD

# Invoke the Lambda function
echo -e "${YELLOW}Invoking Lambda function...${NC}"
aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --payload file://$TMP_PAYLOAD \
  --region $REGION \
  --cli-binary-format raw-in-base64-out \
  /tmp/lambda-output.txt

LAMBDA_EXIT_CODE=$?

echo -e "${YELLOW}Lambda response:${NC}"
cat /tmp/lambda-output.txt

if [ $LAMBDA_EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}Lambda function invoked successfully!${NC}"
  
  # Step 5: Check the database for the vector
  echo -e "${YELLOW}Step 5: Checking database for the vector...${NC}"
  
  # Wait a moment for database insertion to complete
  echo -e "${YELLOW}Waiting 5 seconds for database insertion...${NC}"
  sleep 5
  
  # Get database credentials from Secrets Manager
  echo -e "${YELLOW}Retrieving database credentials...${NC}"
  SECRET_ID="${STACK_NAME}-db-password"
  SECRET_ARN=$(aws secretsmanager describe-secret --secret-id $SECRET_ID --region $REGION --query "ARN" --output text)
  DB_CREDS=$(aws secretsmanager get-secret-value --secret-id "$SECRET_ARN" --region $REGION --query SecretString --output text)
  DB_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION \
    --query "Stacks[0].Outputs[?OutputKey=='DBClusterEndpoint'].OutputValue" --output text)
  
  # Get cluster ARN
  echo -e "${YELLOW}Getting database cluster ARN...${NC}"
  CLUSTER_ARN=$(aws rds describe-db-clusters --db-cluster-identifier "${STACK_NAME}-db" --region $REGION --query "DBClusters[0].DBClusterArn" --output text)
  
  echo -e "${GREEN}Database Endpoint: $DB_ENDPOINT${NC}"
  echo -e "${GREEN}Cluster ARN: $CLUSTER_ARN${NC}"
  
  # Create a Python script for checking vectors
  echo -e "${YELLOW}Creating database query script...${NC}"
  TMP_SCRIPT=$(mktemp)
  cat > "$TMP_SCRIPT" << 'EOF'
import boto3
import sys
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
    SELECT COUNT(*) as count
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
            print(json.dumps({"found": True, "count": count}))
            return 0
        else:
            print(json.dumps({"found": False, "count": 0}))
            return 1
    
    print(json.dumps({"found": False, "error": "No records returned"}))
    return 1

if __name__ == "__main__":
    sys.exit(main())
EOF
  
  # Run the Python script to check for vectors
  echo -e "${YELLOW}Checking database for vectors...${NC}"
  RESULT=$(python3 $TMP_SCRIPT --region $REGION --cluster-arn "$CLUSTER_ARN" --secret-arn "$SECRET_ARN" --filename "$FILENAME")
  
  # Parse the JSON result
  FOUND=$(echo $RESULT | jq -r '.found')
  
  if [ "$FOUND" == "true" ]; then
      COUNT=$(echo $RESULT | jq -r '.count')
      echo -e "${GREEN}Success! Found $COUNT vector(s) in the database.${NC}"
      
      # Clean up
      rm $TMP_SCRIPT
      rm $TMP_PAYLOAD
      
      echo -e "${GREEN}✅ Test completed successfully!${NC}"
      echo -e "${GREEN}The document has been processed and vectorized.${NC}"
      exit 0
  else
      echo -e "${RED}❌ No vectors found in the database.${NC}"
      echo -e "${YELLOW}This suggests the Lambda function did not successfully store vectors.${NC}"
      
      # Clean up
      rm $TMP_SCRIPT
      rm $TMP_PAYLOAD
      
      exit 1
  fi
else
  echo -e "${RED}❌ Failed to invoke Lambda function. Exit code: $LAMBDA_EXIT_CODE${NC}"
  rm $TMP_PAYLOAD
  exit 1
fi
