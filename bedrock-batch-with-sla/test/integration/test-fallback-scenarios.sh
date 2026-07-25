#!/bin/bash
set -e

# Bedrock Batch SLA Fallback - Integration Test Script
# Tests all three fallback scenarios

REGION="${AWS_DEFAULT_REGION:-us-east-1}"
AWS_PROFILE_FLAG=""
if [ -n "${AWS_PROFILE}" ]; then
    AWS_PROFILE_FLAG="--profile ${AWS_PROFILE}"
fi
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text ${AWS_PROFILE_FLAG})
STATE_MACHINE_ARN="arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:bedrock-batch-sla-fallback"
INPUT_BUCKET="bedrock-batch-sla-input-${ACCOUNT_ID}"
OUTPUT_BUCKET="bedrock-batch-sla-output-${ACCOUNT_ID}"
JOBS_TABLE="bedrock-batch-sla-jobs"
ALARM_NAME="bedrock-batch-sla-stuck-job"

echo "🧪 Bedrock Batch SLA Fallback - Integration Tests"
echo "=================================================="
echo ""
echo "⚠️  WARNING: These tests will:"
echo "   - Deploy CDK stack with modified settings"
echo "   - Trigger CloudWatch alarms"
echo "   - Temporarily modify IAM permissions"
echo "   - Create and stop batch jobs"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

# Helper functions
wait_for_execution_state() {
    local exec_arn=$1
    local expected_state=$2
    local max_wait=${3:-300}
    local elapsed=0

    echo "⏳ Waiting for execution to reach $expected_state (max ${max_wait}s)..."
    while [ $elapsed -lt $max_wait ]; do
        STATUS=$(aws stepfunctions describe-execution \
            --execution-arn "$exec_arn" \
            --query 'status' \
            --output text ${AWS_PROFILE_FLAG} 2>/dev/null || echo "UNKNOWN")

        if [ "$STATUS" = "$expected_state" ]; then
            echo "✅ Execution reached $expected_state"
            return 0
        elif [ "$STATUS" = "FAILED" ]; then
            echo "❌ Execution failed unexpectedly"
            return 1
        fi

        sleep 5
        elapsed=$((elapsed + 5))
    done

    echo "⏰ Timeout waiting for $expected_state"
    return 1
}

get_latest_execution() {
    aws stepfunctions list-executions \
        --state-machine-arn "$STATE_MACHINE_ARN" \
        --max-results 1 \
        --output json ${AWS_PROFILE_FLAG} | jq -r '.executions[0].executionArn'
}

check_fallback_path() {
    local exec_arn=$1
    echo "🔍 Checking if fallback path was executed..."

    HISTORY=$(aws stepfunctions get-execution-history \
        --execution-arn "$exec_arn" \
        --output json ${AWS_PROFILE_FLAG})

    # Check for key fallback states
    FALLBACK_ENTRY=$(echo "$HISTORY" | jq '[.events[] | select(.stateEnteredEventDetails.name == "FallbackEntry")] | length')
    RECONCILE=$(echo "$HISTORY" | jq '[.events[] | select(.stateEnteredEventDetails.name == "ReconcileRecords")] | length')
    REDRIVE=$(echo "$HISTORY" | jq '[.events[] | select(.stateEnteredEventDetails.name == "RedriveOnDemand")] | length')
    MERGE=$(echo "$HISTORY" | jq '[.events[] | select(.stateEnteredEventDetails.name == "MergeResults")] | length')

    if [ "$FALLBACK_ENTRY" -gt 0 ]; then
        echo "  ✅ FallbackEntry state reached"
    else
        echo "  ❌ FallbackEntry state NOT reached"
        return 1
    fi

    if [ "$RECONCILE" -gt 0 ]; then
        echo "  ✅ ReconcileRecords executed"
    fi

    if [ "$MERGE" -gt 0 ]; then
        echo "  ✅ MergeResults executed"
    fi

    return 0
}

restore_normal_config() {
    echo "🔄 Restoring normal configuration..."
    npx cdk deploy --require-approval never --ci ${AWS_PROFILE_FLAG} > /dev/null 2>&1
}

# =============================================================================
# TEST 1: Timeout Fallback
# =============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "TEST 1: Timeout Fallback (Step Functions timeout)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

echo "📝 Step 1: Deploy with very short SLA (2 minutes)..."
npx cdk deploy -c slaTotalMinutes=2 --require-approval never --ci ${AWS_PROFILE_FLAG} > /dev/null 2>&1
echo "✅ Deployed with 2-minute SLA"

echo ""
echo "📤 Step 2: Upload test file..."
TEST_FILE="test-timeout-$(date +%s).jsonl"
aws s3 cp sample/input.jsonl "s3://$INPUT_BUCKET/$TEST_FILE" ${AWS_PROFILE_FLAG} > /dev/null 2>&1
echo "✅ Uploaded: $TEST_FILE"

echo ""
echo "⏱️  Step 3: Wait for timeout (WaitForBatchCompletion should timeout in ~60s)..."
sleep 10
EXEC_ARN=$(get_latest_execution)
echo "   Execution: $EXEC_ARN"

# Wait longer for job to populate metrics
sleep 60
echo "   Checking execution status..."

STATUS=$(aws stepfunctions describe-execution --execution-arn "$EXEC_ARN" --query 'status' --output text ${AWS_PROFILE_FLAG})
echo "   Current status: $STATUS"

echo ""
echo "🔍 Step 4: Verify fallback path executed..."
if check_fallback_path "$EXEC_ARN"; then
    echo "✅ TEST 1 PASSED: Timeout fallback worked!"
else
    echo "❌ TEST 1 FAILED: Fallback path not detected"
fi

# Wait for execution to complete or fail
echo ""
echo "⏳ Waiting for execution to complete..."
if wait_for_execution_state "$EXEC_ARN" "SUCCEEDED" 600; then
    echo "✅ Execution completed successfully"
else
    echo "⚠️  Execution did not complete in expected time"
fi

restore_normal_config

# =============================================================================
# TEST 2: Stuck Job Alarm Fallback
# =============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "TEST 2: Stuck Job Alarm Fallback (CloudWatch alarm trigger)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

echo "📤 Step 1: Upload test file and start batch job..."
TEST_FILE="test-alarm-$(date +%s).jsonl"
aws s3 cp sample/input.jsonl "s3://$INPUT_BUCKET/$TEST_FILE" ${AWS_PROFILE_FLAG} > /dev/null 2>&1
echo "✅ Uploaded: $TEST_FILE"

echo ""
echo "⏳ Step 2: Wait for job to reach InProgress with metrics (90s)..."
sleep 10
EXEC_ARN=$(get_latest_execution)
echo "   Execution: $EXEC_ARN"

# Wait longer for job to populate metrics
sleep 80

# Check if execution is running
STATUS=$(aws stepfunctions describe-execution --execution-arn "$EXEC_ARN" --query 'status' --output text ${AWS_PROFILE_FLAG})
if [ "$STATUS" != "RUNNING" ]; then
    echo "⚠️  Execution not running, skipping alarm test"
else
    # Verify job has metrics populated
    JOB_ID=$(echo "$EXEC_ARN" | grep -oE '[a-f0-9-]{36}$')
    JOB_ARN=$(aws dynamodb get-item \
        --table-name "$JOBS_TABLE" \
        --key "{\"JobId\":{\"S\":\"$JOB_ID\"}}" \
        --output json ${AWS_PROFILE_FLAG} | jq -r '.Item.BedrockJobArn.S')

    if [ "$JOB_ARN" != "null" ] && [ -n "$JOB_ARN" ]; then
        RECORD_COUNT=$(aws bedrock get-model-invocation-job \
            --job-identifier "$JOB_ARN" \
            --query 'inputDataConfig.s3InputDataConfig.recordCount' \
            --output text ${AWS_PROFILE_FLAG} 2>/dev/null || echo "0")
        echo "   Job has $RECORD_COUNT records (metrics populated)"
    fi

    echo ""
    echo "🚨 Step 3: Manually trigger CloudWatch alarm..."
    aws cloudwatch set-alarm-state \
        --alarm-name "$ALARM_NAME" \
        --state-value ALARM \
        --state-reason "Integration test: simulating stuck job" ${AWS_PROFILE_FLAG} > /dev/null 2>&1
    echo "✅ Alarm triggered"

    echo ""
    echo "⏳ Step 4: Wait for Trigger Lambda to process alarm (60s)..."
    sleep 60

    echo ""
    echo "🔍 Step 5: Verify fallback was triggered..."
    if check_fallback_path "$EXEC_ARN"; then
        echo "✅ TEST 2 PASSED: Alarm fallback worked!"
    else
        echo "❌ TEST 2 FAILED: Fallback path not detected"
    fi

    # Reset alarm
    echo ""
    echo "🔄 Resetting alarm to OK state..."
    aws cloudwatch set-alarm-state \
        --alarm-name "$ALARM_NAME" \
        --state-value OK \
        --state-reason "Integration test complete" ${AWS_PROFILE_FLAG} > /dev/null 2>&1
fi

# =============================================================================
# TEST 3: Failed Job Fallback
# =============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "TEST 3: Failed Job Fallback (EventBridge event trigger)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

echo "🔒 Step 1: Temporarily deny InvokeModel permission..."
aws iam put-role-policy \
    --role-name bedrock-batch-sla-service-role \
    --policy-name TestDenyInvokeModel \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Deny",
            "Action": "bedrock:InvokeModel",
            "Resource": "*"
        }]
    }' ${AWS_PROFILE_FLAG} > /dev/null 2>&1
echo "✅ Permission denied (temporary)"

echo ""
echo "📤 Step 2: Upload test file (will fail during processing)..."
TEST_FILE="test-failed-$(date +%s).jsonl"
aws s3 cp sample/input.jsonl "s3://$INPUT_BUCKET/$TEST_FILE" ${AWS_PROFILE_FLAG} > /dev/null 2>&1
echo "✅ Uploaded: $TEST_FILE"

echo ""
echo "⏳ Step 3: Poll until job fails (max 10 minutes)..."
sleep 10
EXEC_ARN=$(get_latest_execution)
echo "   Execution: $EXEC_ARN"

JOB_ID=$(echo "$EXEC_ARN" | grep -oE '[a-f0-9-]{36}$')
echo "   Job ID: $JOB_ID"

echo ""
echo "🔍 Step 4: Monitoring job status until Failed..."
JOB_FAILED=false
for i in {1..40}; do
    JOB_ARN=$(aws dynamodb get-item \
        --table-name "$JOBS_TABLE" \
        --key "{\"JobId\":{\"S\":\"$JOB_ID\"}}" \
        --output json ${AWS_PROFILE_FLAG} 2>/dev/null | jq -r '.Item.BedrockJobArn.S')

    if [ "$JOB_ARN" != "null" ] && [ -n "$JOB_ARN" ] && [ "$JOB_ARN" != "None" ]; then
        BEDROCK_STATUS=$(aws bedrock get-model-invocation-job \
            --job-identifier "$JOB_ARN" \
            --query 'status' \
            --output text ${AWS_PROFILE_FLAG} 2>/dev/null || echo "UNKNOWN")

        echo "   [$i] Bedrock job status: $BEDROCK_STATUS"

        if [ "$BEDROCK_STATUS" = "Failed" ]; then
            echo "✅ Job failed as expected!"
            JOB_FAILED=true
            break
        elif [ "$BEDROCK_STATUS" = "Completed" ]; then
            echo "⚠️  Job completed (should have failed due to denied permissions)"
            break
        fi
    else
        echo "   [$i] Waiting for job ARN to be recorded..."
    fi

    sleep 15
done

if [ "$JOB_FAILED" = true ]; then
    echo ""
    echo "⏳ Waiting for EventBridge to trigger fallback (60s)..."
    sleep 60

    echo ""
    echo "🔍 Step 5: Verify fallback was triggered..."
    if check_fallback_path "$EXEC_ARN"; then
        echo "✅ TEST 3 PASSED: Failed job fallback worked!"
    else
        echo "❌ TEST 3 FAILED: Fallback path not detected"
    fi
else
    echo "❌ TEST 3 FAILED: Job did not fail within timeout"
fi

echo ""
echo "🔓 Step 6: Restore InvokeModel permission..."
aws iam delete-role-policy \
    --role-name bedrock-batch-sla-service-role \
    --policy-name TestDenyInvokeModel ${AWS_PROFILE_FLAG} > /dev/null 2>&1
echo "✅ Permissions restored"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "TEST SUMMARY"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "✅ Test 1: Timeout Fallback - Check execution logs"
echo "⚠️  Test 2: Alarm Fallback - Check execution logs"
echo "⚠️  Test 3: Failed Job Fallback - Check execution logs"
echo ""
echo "📊 View executions:"
echo "https://console.aws.amazon.com/states/home?region=$REGION#/statemachines/view/$STATE_MACHINE_ARN"
echo ""
echo "💡 Note: Some fallback paths may take additional time to complete."
echo "   Check the Step Functions console for full execution details."
echo ""
