#!/usr/bin/env python3
import aws_cdk as cdk
from stack import BedrockBatchSlaFallbackStack

app = cdk.App()

model_id = app.node.try_get_context("modelId") or "us.anthropic.claude-sonnet-4-6"
sla_total_minutes = int(app.node.try_get_context("slaTotalMinutes") or 360)
stuck_threshold_minutes = int(app.node.try_get_context("stuckThresholdMinutes") or 30)
max_concurrency = int(app.node.try_get_context("maxConcurrency") or 20)
safety_buffer_minutes = int(app.node.try_get_context("safetyBufferMinutes") or 10)

BedrockBatchSlaFallbackStack(
    app,
    "BedrockBatchSlaFallbackStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
    description="Bedrock Batch Inference with On-Demand SLA Fallback",
    tags={"project": "bedrock-batch-sla"},
    model_id=model_id,
    sla_total_minutes=sla_total_minutes,
    stuck_threshold_minutes=stuck_threshold_minutes,
    max_concurrency=max_concurrency,
    safety_buffer_minutes=safety_buffer_minutes,
)

app.synth()
