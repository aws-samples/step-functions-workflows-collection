from aws_cdk import (
    aws_stepfunctions as sfn,
    aws_iam as iam,
    aws_athena as athena,
    CfnOutput as CfnOutput,
    aws_lambda as lambda_,
    Aws, Duration
)
import json

from aws_cdk.aws_lambda import Runtime
from constructs import Construct

RAW_SOURCE_PREFIX = "raw_source"
ATHENA_RESULTS_PREFIX = "athena_results"
FORMATTED_RESULTS_PREFIX = "formatted"
WAIT_TIME_IN_SECS = 25
QUERY_NUMBER_OF_OCCURRENCES_OF_STORM_EVENT_BY_TYPE_AND_STATE = \
    "SELECT YEAR, STATE, EVENT_TYPE, COUNT(EVENT_TYPE) as NUMBER_OF_OCCURRENCES FROM storm_events_db.details GROUP BY " \
    "YEAR, STATE, EVENT_TYPE ORDER BY YEAR, STATE"


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

        return lambda_.Function(
            self, 'DecompressStormData',
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset('ingest_and_analyze_historical_storm_events/lambda/ingest_and_decompress'),
            handler='index.decompress',
            role=decompress_gz_lambda_role,
            environment={
                 "raw_source_bucket": self.source_bucket.bucket_name
            },
            timeout=Duration.minutes(10)
        )
        # return python.PythonFunction(self, "DecompressSevereWeatherDataRecord",
        #                              entry="./ingest_and_analyze_historical_storm_events"
        #                                    "/lambda/ingest_and_decompress",
        #                              runtime=Runtime.PYTHON_3_9,  # required
        #                              index="index.py",
        #                              handler="decompress",
        #                              environment={
        #                                  "raw_source_bucket": self.source_bucket.bucket_name
        #                              },
        #                              role=decompress_gz_lambda_role,
        #                              timeout=Duration.minutes(10)
        #                              )

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
        asl = self.build_ingestion_workflow_definition(decompress_lambda.function_arn, athena_workgroup.name)
        role = self.get_ingestion_workflow_role()

        role.add_to_policy(iam.PolicyStatement(
            resources=[decompress_lambda.function_arn],
            actions=["lambda:InvokeFunction"]
        ))

        state_machine = sfn.CfnStateMachine(self, "IngestAndAnalyzeStormEvents",
                            definition=asl,
                            role_arn=role.role_arn
                            )

        # CfnOutput(self, "IngestionWorkflow", value=state_machine.state_machine_name)

    def build_ingestion_workflow_definition(self, decompress_lambda_arn, athena_workgroupname):
        asl = {
            "Comment": "A description of my state machine",
            "StartAt": "Ingest From S3",
            "States": {
                "Ingest From S3": {
                    "Type": "Map",
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ItemReaderFailed"],
                            "Next": "Fail"
                        }
                    ],
                    "Next": "Ingestion Complete",
                    "ItemProcessor": {
                        "ProcessorConfig": {
                            "Mode": "DISTRIBUTED",
                            "ExecutionType": "STANDARD"
                        },
                        "StartAt": "Decompress File",
                        "States": {
                            "Decompress File": {
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
                    }

                },
                "Crawl Storm Data": {
                    "Type": "Task",
                    "Next": "Wait",
                    "Parameters": {
                        "Name": self.crawler_name
                    },
                    "Resource": "arn:aws:states:::aws-sdk:glue:startCrawler",
                    "Retry": [
                        {
                            "ErrorEquals": [
                                "Glue.CrawlerRunningException"
                            ],
                            "IntervalSeconds": 60,
                            "MaxAttempts": 6,
                            "BackoffRate": 1
                        }
                    ]
                },
                "Wait": {
                    "Type": "Wait",
                    "Seconds": WAIT_TIME_IN_SECS,
                    "Next": "Get Crawler Status"
                },
                "Get Crawler Status": {
                    "Type": "Task",
                    "Parameters": {
                        "Name": self.crawler_name
                    },
                    "Resource": "arn:aws:states:::aws-sdk:glue:getCrawler",
                    "Next": "Is Crawler READY?"
                },
                "Is Crawler READY?": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.Crawler.State",
                            "StringEquals": "READY",
                            "Next": "Query Storm Data"
                        }
                    ],
                    "Default": "Wait"
                },
                "Ingestion Complete": {
                    "Type": "Pass",
                    "Next": "Crawl Storm Data"
                },
                "Query Storm Data": {
                    "End": True,
                    "Parameters": {
                        "QueryString": QUERY_NUMBER_OF_OCCURRENCES_OF_STORM_EVENT_BY_TYPE_AND_STATE,
                        "WorkGroup": athena_workgroupname,
                        "QueryExecutionContext": {
                            "Database": "storm_events_db",
                            "Catalog": "AwsDataCatalog"
                        }
                    },
                    "Resource": "arn:aws:states:::athena:startQueryExecution.sync",
                    "Type": "Task"
                },
                "Fail": {
                    "Type": "Fail"
                }
            }
        }

        return asl
