from aws_cdk import (
    # Duration,
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    CfnOutput as CfnOutput,
)
from constructs import Construct
from migrate_csv_to_ddb_distributed_map.migration_workflow import MigrationWorkflow

TABLE_NAME = "tb_ev_vehicle_data"
DDB_SDK_RETRIES_CONFIG = 10

import migrate_csv_to_ddb_distributed_map.constants as constants


class MigrateCSVToDdbDistributedMapStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        source_bucket = self.build_source_bucket()
        ddb_table = self.build_destination_table()

        migration_workflow = MigrationWorkflow(
            self,
            "MigrationWorkflow",
            source_bucket=source_bucket,
            destination_ddb_table=ddb_table,
            ddb_sdk_retries_config=DDB_SDK_RETRIES_CONFIG,
        )
        migration_workflow.build()

        CfnOutput(self, "SourceBucket", value=source_bucket.bucket_name)

    def build_source_bucket(self):
        return s3.Bucket(
            self,
            "MigrationSourceBucket",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

    def build_destination_table(self):
        return dynamodb.Table(
            self,
            "MigrationDestinationTable",
            partition_key=dynamodb.Attribute(
                name=constants.DB_PARTITION_KEY, type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            table_name=TABLE_NAME,
        )
