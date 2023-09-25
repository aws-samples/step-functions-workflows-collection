#!/bin/bash

STACK=$(sed -nr '/stack_name/{s/stack_name = "(.*)"/\1/;p;}' samconfig.toml)
REGION=$(sed -nr '/region/{s/region = "(.*)"/\1/;p;}' samconfig.toml)

ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name $STACK \
        --query "Stacks[].Outputs[?OutputKey=='RestApiEndpoint'].OutputValue" \
        --output text) 

RESPONSE=$(curl -XPOST --silent $ENDPOINT | jq)
EXEARN=$(echo $RESPONSE | jq '.workflow.executionArn')
LAMBDAURL=$(echo $RESPONSE | jq -r '.workflow.completeLambdaResultURL')

printf "Start Step Functions workflow with ARN: $EXEARN\n\n"
printf "Streaming results from Lambda URL: $LAMBDAURL\n\n"
printf "Results:\n\n"

curl -N $LAMBDAURL \
  --aws-sigv4 aws:amz:$REGION:lambda \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" \
  --header "x-amz-security-token: $AWS_SESSION_TOKEN" \
