import aws_cdk as cdk
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_dynamodb as dynamodb
from constructs import Construct


class StorageConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, account_id: str,
                 removal_policy: cdk.RemovalPolicy = cdk.RemovalPolicy.DESTROY) -> None:
        super().__init__(scope, construct_id)

        self.input_bucket = s3.Bucket(
            self, "InputBucket",
            bucket_name=f"bedrock-batch-sla-input-{account_id}",
            removal_policy=removal_policy,
            auto_delete_objects=(removal_policy == cdk.RemovalPolicy.DESTROY),
            event_bridge_enabled=True,
            versioned=False,
        )

        self.output_bucket = s3.Bucket(
            self, "OutputBucket",
            bucket_name=f"bedrock-batch-sla-output-{account_id}",
            removal_policy=removal_policy,
            auto_delete_objects=(removal_policy == cdk.RemovalPolicy.DESTROY),
            versioned=False,
        )

        self.jobs_table = dynamodb.Table(
            self, "JobsTable",
            table_name="bedrock-batch-sla-jobs",
            partition_key=dynamodb.Attribute(name="JobId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            # No TTL — retain job records for analytics. Add based on your retention policy.
            point_in_time_recovery=False,
        )

        self.jobs_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(name="Status", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="CreatedAt", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        self.jobs_table.add_global_secondary_index(
            index_name="BedrockJobArnIndex",
            partition_key=dynamodb.Attribute(name="BedrockJobArn", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )
