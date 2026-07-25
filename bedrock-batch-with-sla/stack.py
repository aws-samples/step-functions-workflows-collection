import aws_cdk as cdk
from constructs import Construct
from cdk_constructs.storage_construct import StorageConstruct
from cdk_constructs.bedrock_service_construct import BedrockServiceConstruct
from cdk_constructs.lambda_compute_construct import LambdaComputeConstruct
from cdk_constructs.orchestration_construct import OrchestrationConstruct
from cdk_constructs.monitoring_construct import MonitoringConstruct


class BedrockBatchSlaFallbackStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        model_id: str,
        sla_total_minutes: int,
        stuck_threshold_minutes: int,
        max_concurrency: int,
        safety_buffer_minutes: int,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Calculate SLA timing
        estimated_on_demand_drain_minutes = 30
        batch_cutoff_minutes = max(
            1,
            sla_total_minutes - estimated_on_demand_drain_minutes - safety_buffer_minutes,
        )
        batch_cutoff_seconds = batch_cutoff_minutes * 60
        timeout_duration_hours = max(24, -(-sla_total_minutes // 60))  # ceiling division

        # Storage: S3 buckets and DynamoDB table
        storage = StorageConstruct(self, "Storage", account_id=self.account)

        # Bedrock service role
        bedrock_service = BedrockServiceConstruct(
            self,
            "BedrockService",
            input_bucket=storage.input_bucket,
            output_bucket=storage.output_bucket,
            model_id=model_id,
        )

        # Lambda compute: all 6 Lambda functions with X-Ray tracing
        compute = LambdaComputeConstruct(
            self,
            "Compute",
            jobs_table=storage.jobs_table,
            input_bucket=storage.input_bucket,
            output_bucket=storage.output_bucket,
            bedrock_service_role_arn=bedrock_service.service_role_arn,
            model_id=model_id,
            timeout_duration_hours=timeout_duration_hours,
            batch_cutoff_seconds=batch_cutoff_seconds,
            max_concurrency=max_concurrency,
            stuck_threshold_minutes=stuck_threshold_minutes,
        )

        # Orchestration: Step Functions state machine
        orchestration = OrchestrationConstruct(
            self,
            "Orchestration",
            region=self.region,
            store_token_fn=compute.store_token_fn,
            reconcile_fn=compute.reconcile_fn,
            merge_fn=compute.merge_fn,
            bedrock_service_role_arn=bedrock_service.service_role_arn,
            jobs_table=storage.jobs_table,
            output_bucket=storage.output_bucket,
            model_id=model_id,
            batch_cutoff_seconds=batch_cutoff_seconds,
            timeout_duration_hours=timeout_duration_hours,
            max_concurrency=max_concurrency,
        )

        # Resolve circular dependency: Registrar needs State Machine ARN
        compute.update_registrar_state_machine_arn(orchestration.state_machine_arn)

        # Monitoring: CloudWatch alarms, SNS, EventBridge, S3 notifications
        MonitoringConstruct(
            self,
            "Monitoring",
            model_id=model_id,
            stuck_threshold_minutes=stuck_threshold_minutes,
            input_bucket=storage.input_bucket,
            resume_fn=compute.resume_fn,
            trigger_fn=compute.trigger_fn,
            registrar_fn=compute.registrar_fn,
        )

        # Outputs
        cdk.CfnOutput(self, "InputBucketName", value=storage.input_bucket.bucket_name,
                      description="S3 bucket for input JSONL files")
        cdk.CfnOutput(self, "OutputBucketName", value=storage.output_bucket.bucket_name,
                      description="S3 bucket for output results")
        cdk.CfnOutput(self, "StateMachineArn", value=orchestration.state_machine_arn,
                      description="Step Functions state machine ARN")
        cdk.CfnOutput(self, "JobsTableName", value=storage.jobs_table.table_name,
                      description="DynamoDB table for job tracking")
        cdk.CfnOutput(self, "BatchCutoffMinutes", value=str(batch_cutoff_minutes),
                      description="Calculated batch job cutoff time in minutes")
