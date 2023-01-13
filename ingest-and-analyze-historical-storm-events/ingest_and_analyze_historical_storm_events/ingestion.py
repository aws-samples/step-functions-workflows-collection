from aws_cdk import (
    aws_stepfunctions as sfn,
    aws_lambda_python_alpha as python,
    aws_iam as iam,
    aws_athena as athena,
    Aws, Duration
)
import json

from aws_cdk.aws_lambda import Runtime
from constructs import Construct

RAW_SOURCE_PREFIX = "raw_source"
ATHENA_RESULTS_PREFIX = "athena_results"
FORMATTED_RESULTS_PREFIX = "formatted"
WAIT_TIME_IN_SECS = 25

class IngestionWorkflow(Construct):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            source_bucket,
            crawler_name
    ) -> None:
        super().__init__(scope, construct_id)
        self.source_bucket = source_bucket
        self.crawler_name = crawler_name

    def get_ingestion_workflow_role(self):
        ingestion_workflow_role = iam.Role(self, "IngestionWorkflowRole",
                                           assumed_by=iam.ServicePrincipal("states.amazonaws.com")
                                           )

        ingestion_workflow_role.add_to_policy(iam.PolicyStatement(
            resources=[
                f"{self.source_bucket.bucket_arn}",
                f"{self.source_bucket.bucket_arn}/{FORMATTED_RESULTS_PREFIX}/*",
                f"{self.source_bucket.bucket_arn}/{ATHENA_RESULTS_PREFIX}/*",
            ],
            actions=["s3:*"]
        ))

        ingestion_workflow_role.add_to_policy(iam.PolicyStatement(
            resources=["*"],
            actions=["iam:PassRole"]
        ))

        ingestion_workflow_role.add_to_policy(iam.PolicyStatement(
            resources=["*"],
            actions=["states:StartExecution"]
        ))

        ingestion_workflow_role.add_to_policy(iam.PolicyStatement(
            resources=["*"],
            actions=["glue:*"]
        ))
        ingestion_workflow_role.add_to_policy(iam.PolicyStatement(
            resources=["*"],
            actions=["athena:*"]
        ))

        return ingestion_workflow_role

    def build_decompress_lambda(self):
        decompress_gz_lambda_role = iam.Role(self, "DecompressGZLambdaRole",
                                             assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
                                             )

        decompress_gz_lambda_role.add_to_policy(iam.PolicyStatement(
            resources=[f"{self.source_bucket.bucket_arn}/*"],
            actions=["s3:*"]
        ))

        decompress_gz_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))

        return python.PythonFunction(self, "DecompressSevereWeatherDataRecord",
                                     entry="./ingest_and_analyze_historical_storm_events"
                                           "/lambda/ingest_and_decompress",
                                     runtime=Runtime.PYTHON_3_9,  # required
                                     index="index.py",
                                     handler="decompress",
                                     environment={
                                         "raw_source_bucket": self.source_bucket.bucket_name
                                     },
                                     role=decompress_gz_lambda_role,
                                     timeout=Duration.minutes(10)
                                     )

    def build_athena_workgroup(self):
        return athena.CfnWorkGroup(self,
                                   "StormEventsAthenaWorkgroup",
                                   name="storm_events_workgroup",
                                   state="ENABLED",
                                   recursive_delete_option=True,
                                   work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                                       enforce_work_group_configuration=False,
                                       engine_version=athena.CfnWorkGroup.EngineVersionProperty(
                                           effective_engine_version="Athena engine version 2",
                                           selected_engine_version="AUTO"
                                       ),
                                       publish_cloud_watch_metrics_enabled=False,
                                       requester_pays_enabled=False,
                                       result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                                           output_location=f"s3://{self.source_bucket.bucket_name}/{ATHENA_RESULTS_PREFIX}"
                                       )
                                   )

                                   )

    def build(self):
        decompress_lambda = self.build_decompress_lambda()
        athena_workgroup = self.build_athena_workgroup()
        asl = self.build_ingestion_workflow_definition(decompress_lambda.function_arn , athena_workgroup.name)
        role = self.get_ingestion_workflow_role()

        role.add_to_policy(iam.PolicyStatement(
            resources=[decompress_lambda.function_arn],
            actions=["lambda:InvokeFunction"]
        ))


        sfn.CfnStateMachine(self, "IngestAndAnalyzeStormEvents",
                            definition=asl,
                            role_arn=role.role_arn
                            )

    def build_ingestion_workflow_definition(self, decompress_lambda_arn, athena_workgroupname):
        asl = {
            "Comment": "A description of my state machine",
            "StartAt": "IngestFromS3",
            "States": {
                "IngestFromS3": {
                    "Type": "Map",
                    "ItemProcessor": {
                        "ProcessorConfig": {
                            "Mode": "DISTRIBUTED",
                            "ExecutionType": "STANDARD"
                        },
                        "StartAt": "Lambda Invoke",
                        "States": {
                            "Lambda Invoke": {
                                "Type": "Task",
                                "Resource": "arn:aws:states:::lambda:invoke",
                                "OutputPath": "$.Payload",
                                "Parameters": {
                                    "Payload.$": "$",
                                    "FunctionName": decompress_lambda_arn
                                },
                                "Retry": [
                                    {
                                        "ErrorEquals": [
                                            "Lambda.ServiceException",
                                            "Lambda.AWSLambdaException",
                                            "Lambda.SdkClientException",
                                            "Lambda.TooManyRequestsException"
                                        ],
                                        "IntervalSeconds": 2,
                                        "MaxAttempts": 6,
                                        "BackoffRate": 2
                                    }
                                ],
                                "Next": "Pass"
                            },
                            "Pass": {
                                "Type": "Pass",
                                "End": True
                            }
                        }
                    },
                    "Label": "Map",
                    "MaxConcurrency": 1000,
                    "ItemReader": {
                        "Resource": "arn:aws:states:::s3:listObjectsV2",
                        "Parameters": {
                            "Bucket": self.source_bucket.bucket_name,
                            "Prefix": f"{RAW_SOURCE_PREFIX}/"
                        }
                    },
                    "ItemBatcher": {
                        "MaxItemsPerBatch": 5
                    },
                    "Next": "StartStormEventsCrawler"
                },
                "StartStormEventsCrawler": {
                    "Type": "Task",
                    "Next": "Wait",
                    "Parameters": {
                        "Name": self.crawler_name
                    },
                    "Resource": "arn:aws:states:::aws-sdk:glue:startCrawler"
                },
                "Wait": {
                    "Type": "Wait",
                    "Seconds": WAIT_TIME_IN_SECS,
                    "Next": "GetCrawler"
                },
                "GetCrawler": {
                    "Type": "Task",
                    "Parameters": {
                        "Name": self.crawler_name
                    },
                    "Resource": "arn:aws:states:::aws-sdk:glue:getCrawler",
                    "Next": "Crawl complete?"
                },
                "Crawl complete?": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.Crawler.State",
                            "StringEquals": "READY",
                            "Next": "Ingestion Complete"
                        }
                    ],
                    "Default": "Wait"
                },
                "Ingestion Complete": {
                    "Type": "Pass",
                    "Next": "Athena StartQueryExecution"
                },
                "Athena StartQueryExecution": {
                    "End": True,
                    "Parameters": {
                        "QueryString": "SELECT * FROM details limit 10;",
                        "WorkGroup": athena_workgroupname,
                        "QueryExecutionContext": {
                            "Database": "storm_events_db",
                            "Catalog": "AwsDataCatalog"
                        }
                    },
                    "Resource": "arn:aws:states:::athena:startQueryExecution.sync",
                    "Type": "Task"
                },
            }
        }

        return asl
