#!/bin/bash
# Bash deployment script for AWS Feature Relevance Notification System
set -e

SLACK_WEBHOOK_URL=""
BEDROCK_MODEL_ID="us.anthropic.claude-sonnet-4-6"
KNOWLEDGE_BASE_ID=""
STACK_NAME="feature-relevance-poc"
DESTROY_INFRA=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --slack-webhook-url) SLACK_WEBHOOK_URL="$2"; shift 2 ;;
        --bedrock-model-id) BEDROCK_MODEL_ID="$2"; shift 2 ;;
        --knowledge-base-id) KNOWLEDGE_BASE_ID="$2"; shift 2 ;;
        --stack-name) STACK_NAME="$2"; shift 2 ;;
        --destroy-infra) DESTROY_INFRA=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_SCRIPTS_DIR="$SCRIPT_DIR/../../shared/scripts"

echo "=== AWS Feature Relevance Notification System Deployment ==="

# Use shared prerequisites check
echo "Checking prerequisites..."
"$SHARED_SCRIPTS_DIR/check-prerequisites.sh" --min-python-version 3.9

# Get region
if [ -n "$AWS_DEFAULT_REGION" ]; then
    REGION="$AWS_DEFAULT_REGION"
elif [ -n "$AWS_REGION" ]; then
    REGION="$AWS_REGION"
else
    REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
fi
echo "Using region: $REGION"

# Check SAM CLI is installed
echo "Checking AWS SAM CLI..."
if ! command -v sam &> /dev/null; then
    echo "ERROR: AWS SAM CLI not found."
    echo "Install from: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi
echo "  OK: $(sam --version)"

# Destroy mode
if [ "$DESTROY_INFRA" = true ]; then
    echo "Destroying infrastructure..."
    sam delete --stack-name "$STACK_NAME" --region "$REGION" --no-prompts
    echo "Infrastructure destruction completed"
    exit 0
fi

# Build SAM application
echo ""
echo "Building SAM application..."
cd "$SCRIPT_DIR/sam-app"

sam build --template template.yaml
if [ $? -ne 0 ]; then
    echo "ERROR: SAM build failed"
    exit 1
fi
echo "  SAM build succeeded"

# Deploy SAM application
echo ""
echo "Deploying SAM application..."

DEPLOY_ARGS=(
    deploy
    --stack-name "$STACK_NAME"
    --region "$REGION"
    --resolve-s3
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
    --no-confirm-changeset
    --parameter-overrides
    "BedrockModelId=$BEDROCK_MODEL_ID"
    "KnowledgeBaseId=$KNOWLEDGE_BASE_ID"
)

if [ -n "$SLACK_WEBHOOK_URL" ]; then
    DEPLOY_ARGS+=("SlackWebhookUrl=$SLACK_WEBHOOK_URL")
fi

sam "${DEPLOY_ARGS[@]}"
if [ $? -ne 0 ]; then
    echo "ERROR: SAM deploy failed"
    exit 1
fi

# Get stack outputs
echo ""
echo "Getting stack outputs..."
OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs" \
    --output json \
    --region "$REGION" \
    --no-cli-pager 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$OUTPUTS" ]; then
    STATE_MACHINE_ARN=$(echo "$OUTPUTS" | python3 -c "import sys, json; outputs = json.load(sys.stdin); print(next((o['OutputValue'] for o in outputs if o['OutputKey'] == 'StateMachineArn'), ''))" 2>/dev/null)
    RSS_FUNCTION=$(echo "$OUTPUTS" | python3 -c "import sys, json; outputs = json.load(sys.stdin); print(next((o['OutputValue'] for o in outputs if o['OutputKey'] == 'RSSIngestionFunctionName'), ''))" 2>/dev/null)
    SCORER_FUNCTION=$(echo "$OUTPUTS" | python3 -c "import sys, json; outputs = json.load(sys.stdin); print(next((o['OutputValue'] for o in outputs if o['OutputKey'] == 'RelevanceScorerFunctionName'), ''))" 2>/dev/null)
    WORKLOAD_MANAGER=$(echo "$OUTPUTS" | python3 -c "import sys, json; outputs = json.load(sys.stdin); print(next((o['OutputValue'] for o in outputs if o['OutputKey'] == 'WorkloadManagerFunctionName'), ''))" 2>/dev/null)
    PROFILES_TABLE=$(echo "$OUTPUTS" | python3 -c "import sys, json; outputs = json.load(sys.stdin); print(next((o['OutputValue'] for o in outputs if o['OutputKey'] == 'WorkloadProfilesTableName'), ''))" 2>/dev/null)
fi

# Print deployment summary
echo ""
echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
echo ""
echo "  Region:              $REGION"
echo "  Stack Name:          $STACK_NAME"
echo "  State Machine:       $STATE_MACHINE_ARN"
echo "  RSS Ingestion:       $RSS_FUNCTION"
echo "  Relevance Scorer:    $SCORER_FUNCTION"
echo "  Workload Manager:    $WORKLOAD_MANAGER"
echo "  Profiles Table:      $PROFILES_TABLE"
echo ""
echo "Next Steps:"
echo "  1. Create a workload profile:"
echo "     aws lambda invoke --function-name $WORKLOAD_MANAGER \\"
echo "       --cli-binary-format raw-in-base64-out \\"
echo "       --payload '{\"action\":\"create\",\"profile\":{...}}' /tmp/out.json"
echo "  2. Test the pipeline:"
echo "     aws lambda invoke --function-name $RSS_FUNCTION \\"
echo "       --cli-binary-format raw-in-base64-out \\"
echo "       --payload '{\"test_mode\":true}' /tmp/test.json"
echo "  3. Monitor in Step Functions console"
echo ""
echo "To destroy the infrastructure later, run:"
echo "  ./deploy-all.sh --destroy-infra"
