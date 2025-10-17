#!/bin/bash
set -e

# Colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

STACK_NAME="vectorization-pipeline"
REGION=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --region|-r)
      REGION="$2"
      shift 2
      ;;
    --stack-name|-s)
      STACK_NAME="$2"
      shift 2
      ;;
    --skip-db|-d)
      SKIP_DB=true
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo -e "Usage: $0 [--region|-r REGION] [--stack-name|-s STACK_NAME] [--skip-db|-d]"
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

# Build shared layer first
echo -e "${YELLOW}Building shared libraries layer...${NC}"
cd functions/shared
pip install -r requirements.txt -t python/
cd ../..

# Step 1: Deploy main infrastructure stack
echo -e "${YELLOW}STEP 1: Deploying main infrastructure stack...${NC}"
echo -e "${YELLOW}This stack creates the VPC, RDS Aurora PostgreSQL, Lambda functions, but skips DB initialization${NC}"

cd "$(dirname "$0")"  # Ensure we're in the sam-vectorization-pipeline directory

# Deploy main stack with SAM
echo -e "${YELLOW}Deploying main infrastructure with SAM...${NC}"
sam deploy \
  --template-file template.yaml \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --no-fail-on-empty-changeset \
  --force-upload \
  --region $REGION

# Wait for stack to complete
echo -e "${YELLOW}Waiting for main stack deployment to complete...${NC}"
aws cloudformation wait stack-create-complete --stack-name $STACK_NAME --region $REGION || \
aws cloudformation wait stack-update-complete --stack-name $STACK_NAME --region $REGION

echo -e "${GREEN}Main infrastructure stack deployed successfully!${NC}"

# Step 2: Initialize the database (unless skipped)
if [ "$SKIP_DB" = true ]; then
  echo -e "${YELLOW}STEP 2: Skipping database initialization as requested${NC}"
  echo -e "${YELLOW}You can initialize the database later using:${NC}"
  echo -e "${YELLOW}  ./deploy-db-init.sh --region $REGION --stack-name $STACK_NAME${NC}"
else
  echo -e "${YELLOW}STEP 2: Initializing the PostgreSQL DB with pgvector extension and tables${NC}"
  
  # Pass the region and stack name to the database initialization script
  # Using the Data API method which is most reliable across environments
  ./deploy-db-init.sh --region $REGION --stack-name $STACK_NAME
  
  echo -e "${GREEN}Database initialization completed!${NC}"
fi

echo -e ""
echo -e "${GREEN}Infrastructure deployment complete!${NC}"
echo -e "${YELLOW}If you need to reinitialize the database, run:${NC}"
echo -e "${YELLOW}  ./deploy-db-init.sh --region $REGION --stack-name $STACK_NAME${NC}"
