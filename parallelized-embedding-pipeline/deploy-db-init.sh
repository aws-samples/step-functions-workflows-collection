#!/bin/bash
set -e

# Colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Database Initialization via Data API${NC}"

# Default values
STACK_NAME="vectorization-pipeline"
REGION=""

# Parse command line arguments
while [[ ${#} -gt 0 ]]; do
  key="${1}"
  case "${key}" in
    --region|-r)
      REGION="${2}"
      shift 2
      ;;
    --stack-name|-s)
      STACK_NAME="${2}"
      shift 2
      ;;
    *)
      echo -e "${RED}Unknown option: ${1}${NC}"
      echo -e "Usage: $0 [--region|-r REGION] [--stack-name|-s STACK_NAME]"
      exit 1
      ;;
  esac
done

# If region is still not set, try to get it from AWS config or use a default
if [ -z "$REGION" ]; then
  REGION=$(aws configure get region)
  if [ -z "$REGION" ]; then
    echo -e "${YELLOW}No region specified, using default: us-west-2${NC}"
    REGION="us-west-2"
  fi
fi

# Make sure we're in the correct directory
cd "$(dirname "${0}")"  # Move to the script's directory

echo -e "${YELLOW}Initializing Database for ${STACK_NAME} in ${REGION}${NC}"
# Check for Python and boto3
echo -e "${YELLOW}Checking Python requirements...${NC}"
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Python 3 is required but not installed.${NC}"
    exit 1
fi

if ! python3 -c "import boto3" &>/dev/null; then
    echo -e "${YELLOW}Installing boto3...${NC}"
    pip3 install boto3 --quiet
fi

# Create a temporary Python script for database initialization
TMP_SCRIPT=$(mktemp)
cat > "$TMP_SCRIPT" << 'EOF'
import boto3
import sys
import time
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', required=True)
    parser.add_argument('--stack-name', required=True)
    return parser.parse_args()

def main():
    args = parse_args()
    region = args.region
    stack_name = args.stack_name
    
    print(f"\033[33mInitializing database in {region} for stack {stack_name}...\033[0m")
    
    # Initialize clients
    rds_data = boto3.client('rds-data', region_name=region)
    secretsmanager = boto3.client('secretsmanager', region_name=region)
    rds = boto3.client('rds', region_name=region)
    
    # Get resources
    db_cluster_id = f"{stack_name}-db"
    secret_id = f"{stack_name}-db-password"
    database_name = "mydb"
    
    print(f"\033[33mRetrieving database resources...{stack_name}\033[0m")
    
    # Get cluster ARN
    response = rds.describe_db_clusters(DBClusterIdentifier=db_cluster_id)
    cluster_arn = response['DBClusters'][0]['DBClusterArn']
    print(f"\033[32mCluster ARN: {cluster_arn}\033[0m")
    
    # Get secret ARN
    response = secretsmanager.describe_secret(SecretId=secret_id)
    secret_arn = response['ARN']
    print(f"\033[32mSecret ARN: {secret_arn}\033[0m")
    
    # SQL statements to execute
    sql_statements = [
        ("CREATE EXTENSION IF NOT EXISTS vector", "Creating pgvector extension"),
        ("""
        CREATE TABLE IF NOT EXISTS vectortable (
            chunk_id VARCHAR(36) PRIMARY KEY,
            workspace_id VARCHAR(100) NOT NULL,
            document_id VARCHAR(100) NOT NULL,
            document_sub_id VARCHAR(100),
            document_type VARCHAR(50),
            document_sub_type VARCHAR(50),
            path VARCHAR(1000),
            title VARCHAR(500),
            content TEXT,
            content_embeddings vector(1536),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """, "Creating vectortable"),
        ("CREATE INDEX IF NOT EXISTS idx_vectortable_workspace_id ON vectortable (workspace_id)", "Creating workspace_id index"),
        ("CREATE INDEX IF NOT EXISTS idx_vectortable_document_id ON vectortable (document_id)", "Creating document_id index"),
        ("CREATE INDEX IF NOT EXISTS idx_vectortable_vector ON vectortable USING ivfflat (content_embeddings vector_l2_ops) WITH (lists = 100)", "Creating vector similarity index")
    ]
    
    # Execute each SQL statement
    for sql, description in sql_statements:
        print(f"\033[33m{description}...\033[0m")
        max_retries = 3
        success = False
        
        for attempt in range(max_retries):
            try:
                response = rds_data.execute_statement(
                    resourceArn=cluster_arn,
                    secretArn=secret_arn,
                    database=database_name,
                    sql=sql
                )
                print(f"\033[32m✓ Success\033[0m")
                success = True
                break
            except Exception as e:
                if "already exists" in str(e):
                    print(f"\033[33m→ Already exists\033[0m")
                    success = True
                    break
                if attempt < max_retries - 1:
                    print(f"\033[31m✗ Attempt {attempt+1}/{max_retries} failed: {e}\033[0m")
                    print(f"\033[33m  Retrying in 3 seconds...\033[0m")
                    time.sleep(3)
                else:
                    print(f"\033[31m✗ All attempts failed: {e}\033[0m")
        
        if not success:
            print(f"\033[31mFailed to execute: {description}\033[0m")
            return 1
    
    print(f"\033[32m✓ Database initialized successfully!\033[0m")
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF

# Execute the Python script
echo -e "${YELLOW}Executing database initialization via Data API...${NC}"
python3 "$TMP_SCRIPT" --region "$REGION" --stack-name "$STACK_NAME"
RESULT=$?

# Clean up
rm "$TMP_SCRIPT"

if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}Database initialization completed successfully!${NC}"
else
    echo -e "${RED}Database initialization failed!${NC}"
    exit $RESULT
fi

echo -e "${GREEN}Database initialization complete!${NC}"
