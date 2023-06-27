from aws_cdk import (
    aws_stepfunctions as sfn,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_kinesisfirehose as kinesisfirehose,
    CfnParameter as CfnParameter,
    CfnCondition as CfnCondition,
    Fn as Fn,
    Aws,
    Duration,
    CfnOutput as CfnOutput,
)
import json
from constructs import Construct
import migrate_csv_to_ddb_distributed_map.constants as constants


class MigrationWorkflow(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        source_bucket,
        destination_ddb_table,
        ddb_sdk_retries_config,
    ) -> None:
        super().__init__(scope, construct_id)
        self.source_bucket = source_bucket
        self.destination_ddb_table = destination_ddb_table
        self.ddb_sdk_retries_config = ddb_sdk_retries_config

    def build_kinesis_firehose_ds_error_records(self):
        firehose_role = iam.Role(
            self,
            "firehose-role",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com"),
        )
        firehose_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=[
                    self.source_bucket.bucket_arn,
                    self.source_bucket.bucket_arn + "/*",
                ],
                actions=[
                    "s3:AbortMultipartUpload",
                    "s3:GetBucketLocation",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:ListBucketMultipartUploads",
                    "s3:PutObject",
                ],
            )
        )

        return kinesisfirehose.CfnDeliveryStream(
            self,
            "migration-errors-ds",
            extended_s3_destination_configuration=kinesisfirehose.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
                bucket_arn=self.source_bucket.bucket_arn,
                buffering_hints=kinesisfirehose.CfnDeliveryStream.BufferingHintsProperty(
                    interval_in_seconds=60
                ),
                prefix="migration_errors/execution_name=!{partitionKeyFromQuery:execution_name}/",
                error_output_prefix="firehose_errors",
                compression_format="UNCOMPRESSED",
                dynamic_partitioning_configuration=kinesisfirehose.CfnDeliveryStream.DynamicPartitioningConfigurationProperty(
                    enabled=True,
                    retry_options=kinesisfirehose.CfnDeliveryStream.RetryOptionsProperty(
                        duration_in_seconds=300
                    ),
                ),
                processing_configuration=kinesisfirehose.CfnDeliveryStream.ProcessingConfigurationProperty(
                    enabled=True,
                    processors=[
                        kinesisfirehose.CfnDeliveryStream.ProcessorProperty(
                            type="MetadataExtraction",
                            parameters=[
                                kinesisfirehose.CfnDeliveryStream.ProcessorParameterProperty(
                                    parameter_name="MetadataExtractionQuery",
                                    parameter_value="{execution_name:.execution_name}",
                                ),
                                kinesisfirehose.CfnDeliveryStream.ProcessorParameterProperty(
                                    parameter_name="JsonParsingEngine",
                                    parameter_value="JQ-1.6",
                                ),
                            ],
                        )
                    ],
                ),
                role_arn=firehose_role.role_arn,
            ),
        )

    def build_consolidate_lambda(self):
        consolidate_lambda_role = iam.Role(
            self,
            "ConsolidateLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        consolidate_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        return lambda_.Function(
            self,
            "ConsolidateLambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset(
                "migrate_csv_to_ddb_distributed_map/lambda/consolidate_lambda"
            ),
            handler="index.handler",
            role=consolidate_lambda_role,
            environment={
                "S3_BUCKET": self.source_bucket.bucket_name,
                "DESTINATION_TABLE_NAME": self.destination_ddb_table.table_name,
            },
            timeout=Duration.minutes(1),
        )

    def build_data_transform_lambda(self, kinesis_firehose_ds):
        data_transform_lambda_role = iam.Role(
            self,
            "DataTransformLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        data_transform_lambda_role.add_to_policy(
            iam.PolicyStatement(
                resources=[f"{self.source_bucket.bucket_arn}/*"], actions=["s3:*"]
            )
        )

        data_transform_lambda_role.add_to_policy(
            iam.PolicyStatement(
                resources=[self.destination_ddb_table.table_arn],
                actions=[
                    "dynamodb:BatchWriteItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                ],
            )
        )

        data_transform_lambda_role.add_to_policy(
            iam.PolicyStatement(
                resources=[kinesis_firehose_ds.attr_arn],
                actions=["firehose:PutRecord", "firehose:PutRecordBatch"],
            )
        )

        data_transform_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        return lambda_.Function(
            self,
            "DataTransformAndSaveLambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset(
                "migrate_csv_to_ddb_distributed_map/lambda/transform_data"
            ),
            handler="index.handler",
            role=data_transform_lambda_role,
            environment={
                "DESTINATION_TABLE_NAME": self.destination_ddb_table.table_name,
                "DDB_RETRIES": str(self.ddb_sdk_retries_config),
                "ERROR_DELIVERY_STREAM_ARN": str(kinesis_firehose_ds.attr_arn),
            },
            timeout=Duration.minutes(15),
        )

    def build_migration_workflow_role(self):
        migration_workflow_role = iam.Role(
            self,
            "MigrationWorkflowRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )

        migration_workflow_role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    f"{self.source_bucket.bucket_arn}",
                    f"{self.source_bucket.bucket_arn}/*",
                ],
                actions=["s3:GetObject"],
            )
        )

        migration_workflow_role.add_to_policy(
            iam.PolicyStatement(resources=["*"], actions=["iam:PassRole"])
        )

        migration_workflow_role.add_to_policy(
            iam.PolicyStatement(resources=["*"], actions=["states:StartExecution"])
        )
        return migration_workflow_role

    def build_migration_workflow_definition(
        self, data_transform_and_save_lambda, consolidate_lambda, publish_results_topic
    ):
        # TODO: OUTPUT SHOULD SHOW RESULTS AFTER SNS PUBLISH

        return {
            "Comment": "Migration Workflow StateMachine",
            "StartAt": "Read Input File",
            "States": {
                "Read Input File": {
                    "Type": "Map",
                    "ItemProcessor": {
                        "ProcessorConfig": {
                            "Mode": "DISTRIBUTED",
                            "ExecutionType": "STANDARD",
                        },
                        "StartAt": "Validate, Transform, and Migrate Items",
                        "States": {
                            "Validate, Transform, and Migrate Items": {
                                "Type": "Task",
                                "Resource": "arn:aws:states:::lambda:invoke",
                                "OutputPath": "$.Payload",
                                "Parameters": {
                                    "Payload.$": "$",
                                    "FunctionName": data_transform_and_save_lambda.function_name,
                                },
                                "Retry": [
                                    {
                                        "ErrorEquals": [
                                            "Lambda.ServiceException",
                                            "Lambda.AWSLambdaException",
                                            "Lambda.SdkClientException",
                                            "Lambda.TooManyRequestsException",
                                        ],
                                        "IntervalSeconds": 2,
                                        "MaxAttempts": 6,
                                        "BackoffRate": 2,
                                    }
                                ],
                                "End": True,
                                "Catch": [
                                    {
                                        "ErrorEquals": ["MigrationError"],
                                        "Next": "Individual map process failed",
                                    }
                                ],
                            },
                            "Individual map process failed": {"Type": "Fail"},
                        },
                    },
                    "ItemReader": {
                        "Resource": "arn:aws:states:::s3:getObject",
                        "ReaderConfig": {
                            "InputType": "CSV",
                            "CSVHeaderLocation": "FIRST_ROW",
                        },
                        "Parameters": {
                            "Bucket.$": "$.bucket_name",
                            "Key.$": "$.file_key",
                        },
                    },
                    "MaxConcurrency": constants.STATE_MACHINE_MAX_CONCURRENCY,
                    "Label": "ReadInputFile",
                    "ItemBatcher": {
                        "MaxItemsPerBatch": constants.MAX_ITEMS_PER_BATCH,
                        "MaxInputBytesPerBatch": constants.MAX_INPUT_BYTES_PER_BATCH,
                        "BatchInput": {"execution_name.$": "$$.Execution.Name"},
                    },
                    "Next": "Consolidate Migration",
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ItemReaderFailed"],
                            "Next": "Migration Failed",
                        }
                    ],
                    "ToleratedFailurePercentage": constants.TOLERATED_FAILURE_PERCENTAGE,
                },
                "Consolidate Migration": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "OutputPath": "$.Payload",
                    "Parameters": {
                        "Payload": {
                            "execution_name.$": "$$.Execution.Name",
                            "report.$": "$",
                        },
                        "FunctionName": consolidate_lambda.function_name,
                    },
                    "Retry": [
                        {
                            "ErrorEquals": [
                                "Lambda.ServiceException",
                                "Lambda.AWSLambdaException",
                                "Lambda.SdkClientException",
                                "Lambda.TooManyRequestsException",
                            ],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 6,
                            "BackoffRate": 2,
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["ConsolidationError"],
                            "Next": "Migration Failed",
                        }
                    ],
                    "Next": "Publish Results",
                },
                "Migration Failed": {"Type": "Fail"},
                "Publish Results": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::sns:publish",
                    "ResultPath": "$.SnsPublish",
                    "Parameters": {
                        "Message.$": "$",
                        "TopicArn": publish_results_topic.topic_arn,
                    },
                    "Next": "Migration Complete",
                },
                "Migration Complete": {"Type": "Pass", "End": True},
            },
        }

    def build_publish_results_resources(self):
        completion_email_target = CfnParameter(
            self,
            "SendCompletionEmailTo",
            type="String",
            description="Migration results will be sent",
            default="",
        ).value_as_string

        publish_results_topic = sns.Topic(self, "PublishMigrationResults")

        # TODO: CONDITIONAL SUBSCRIPTION
        # dont_create_subscription = CfnCondition(self, 'CreateSubscription', CfnCondition.Expression.builder()
        #                                   .condition(Fn.condition_equals(completion_email_target, ''))
        #                                   .build())

        # if completion_email_target.value is not None:
        #     publish_results_topic.add_subscription(
        #         subscriptions.EmailSubscription(email_address=completion_email_target.value_as_string))

        return publish_results_topic

    def build(self):
        kinesis_firehose_ds = self.build_kinesis_firehose_ds_error_records()
        data_transform_and_save_lambda = self.build_data_transform_lambda(
            kinesis_firehose_ds=kinesis_firehose_ds
        )
        consolidate_lambda = self.build_consolidate_lambda()
        migration_workflow_role = self.build_migration_workflow_role()
        publish_results_topic = self.build_publish_results_resources()
        migration_workflow_definition = self.build_migration_workflow_definition(
            data_transform_and_save_lambda, consolidate_lambda, publish_results_topic
        )

        migration_workflow_role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    data_transform_and_save_lambda.function_arn,
                    consolidate_lambda.function_arn,
                ],
                actions=["lambda:InvokeFunction"],
            )
        )

        migration_workflow_role.add_to_policy(
            iam.PolicyStatement(
                resources=[publish_results_topic.topic_arn], actions=["sns:Publish"]
            )
        )

        migration_state_machine = sfn.CfnStateMachine(
            self,
            "MigrationWorkflow",
            definition=migration_workflow_definition,
            role_arn=migration_workflow_role.role_arn,
        )

        CfnOutput(
            self, "PublishMigrationResultsTopic", value=publish_results_topic.topic_arn
        )
        CfnOutput(
            self,
            "MigrationWorkflowStateMachine",
            value=migration_state_machine.attr_name,
        )
