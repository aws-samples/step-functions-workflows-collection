#!/bin/bash

# Colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if python libraries are installed
check_requirements() {
    echo -e "${YELLOW}Checking requirements...${NC}"
    
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}Python 3 is not installed. Please install Python 3 first.${NC}"
        exit 1
    fi
    
    # Check if boto3 is installed
    if ! python3 -c "import boto3" &>/dev/null; then
        echo -e "${YELLOW}boto3 not found. Attempting to install...${NC}"
        
        if command -v pip3 &>/dev/null; then
            pip3 install boto3
            
            if [ "${?}" -ne 0 ]; then
                echo -e "${RED}Failed to install boto3. Please install it manually with 'pip3 install boto3'${NC}"
                exit 1
            else
                echo -e "${GREEN}boto3 installed successfully${NC}"
            fi
        else
            echo -e "${RED}pip3 not found. Please install boto3 manually with 'pip3 install boto3'${NC}"
            exit 1
        fi
    fi
}

# Parse arguments
REGION="us-west-2"
STACK_NAME="vectorization-pipeline"

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
      echo -e "Usage: ${0} [--region|-r REGION] [--stack-name|-s STACK_NAME]"
      exit 1
      ;;
  esac
done

# Make sure we're in the right directory
cd "$(dirname "$0")"

echo -e "${YELLOW}=============================${NC}"
echo -e "${YELLOW}   Database Connection Test${NC}"
echo -e "${YELLOW}=============================${NC}"
echo -e "${YELLOW}Region: ${NC}${GREEN}$REGION${NC}"
echo -e "${YELLOW}Stack:  ${NC}${GREEN}$STACK_NAME${NC}"
echo -e "${YELLOW}=============================${NC}"
echo

# Check requirements
check_requirements

# Run the test script
echo -e "${YELLOW}Starting connection test...${NC}"
python3 ./test_data_api_connection.py --region "$REGION" --stack-name "$STACK_NAME"

if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}✅ Database connection test successful!${NC}"
    echo -e "${GREEN}The Data API is working with your database.${NC}"
    echo 
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "1. ${GREEN}Run database initialization to set up tables:${NC}"
    echo -e "   ${YELLOW}./deploy-db-init.sh --region $REGION --stack-name $STACK_NAME${NC}"
    echo
else
    echo
    echo -e "${RED}❌ Database connection test failed!${NC}"
    echo
    echo -e "${YELLOW}Possible solutions:${NC}"
    echo -e "1. ${YELLOW}Check that your AWS credentials are correctly configured${NC}"
    echo -e "2. ${YELLOW}Verify that the stack '$STACK_NAME' exists in region '$REGION'${NC}"
    echo -e "3. ${YELLOW}Ensure that the database is 'available' in the RDS console${NC}"
    echo -e "4. ${YELLOW}Check that security group rules allow access to the database${NC}"
    echo
fi
