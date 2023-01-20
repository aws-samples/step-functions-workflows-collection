import uuid
import os
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_iam as iam,
    aws_glue as glue,
    CfnOutput as CfnOutput
)

from constructs import Construct
from ingest_and_analyze_historical_storm_events.ingestion import IngestionWorkflow

STORM_EVENTS_CRAWLER_NAME = "storm_events_data_crawler"


class IngestAndAnalyzeHistoricalStormEventsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        source_bucket = self.build_source_bucket()
        self.build_data_analytics(source_bucket=source_bucket)
        ingestion_workflow = IngestionWorkflow(self, "IngestionWorkflowBuilder", source_bucket,
                                               crawler_name=STORM_EVENTS_CRAWLER_NAME)
        ingestion_workflow.build()

        # CfnOutput(self, "IngestionBucket", value=source_bucket.bucket_name)

    def build_source_bucket(self):
        return s3.Bucket(self, 'StormEventsSourceBucket',
                         versioned=True,
                         encryption=s3.BucketEncryption.S3_MANAGED,
                         block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                         enforce_ssl=True)

    def build_data_analytics(self, source_bucket):
        formatted_files_prefix = "formatted"
        details_prefix = "details"
        locations_prefix = "locations"
        fatalities_prefix = "fatalities"

        severe_weather_glue_db = \
            glue.CfnDatabase(self, "StormEventsDatabase",
                             catalog_id=os.environ["CDK_DEFAULT_ACCOUNT"],
                             database_input=glue.CfnDatabase.DatabaseInputProperty(
                                 create_table_default_permissions=[
                                     glue.CfnDatabase.PrincipalPrivilegesProperty(
                                         permissions=["ALL"],
                                         principal=glue.CfnDatabase.DataLakePrincipalProperty(
                                             data_lake_principal_identifier="IAM_ALLOWED_PRINCIPALS"
                                         )
                                     )],
                                 description="Database of severe weather records",
                                 name="storm_events_db"
                             )
                             )

        glue_crawler_role = iam.Role(self, "GlueCrawlerRole",
                                     assumed_by=iam.ServicePrincipal("glue.amazonaws.com")
                                     )
        glue_crawler_role.add_to_policy(iam.PolicyStatement(
            resources=[f"arn:aws:s3:::{source_bucket.bucket_name}/{formatted_files_prefix}/*"],
            actions=["s3:GetObject",
                     "s3:PutObject"]
        ))
        glue_crawler_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"))

        # TODO CREATE GLUE CRAWLER FOR THE S3 BUCKET
        glue.CfnCrawler(self, "StormEventsDataGlueCrawler",
                        database_name=severe_weather_glue_db.database_input.name,
                        name=STORM_EVENTS_CRAWLER_NAME,
                        role=glue_crawler_role.role_arn,
                        recrawl_policy=glue.CfnCrawler.RecrawlPolicyProperty(
                            recrawl_behavior="CRAWL_NEW_FOLDERS_ONLY"
                        ),
                        schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                            delete_behavior="LOG",
                            update_behavior="LOG"
                        ),
                        targets=glue.CfnCrawler.TargetsProperty(
                            s3_targets=[
                                glue.CfnCrawler.S3TargetProperty(
                                    path=f"s3://{source_bucket.bucket_name}/{formatted_files_prefix}/{details_prefix}/",
                                ),
                                glue.CfnCrawler.S3TargetProperty(
                                    path=f"s3://{source_bucket.bucket_name}/{formatted_files_prefix}/{locations_prefix}/",
                                ),
                                glue.CfnCrawler.S3TargetProperty(
                                    path=f"s3://{source_bucket.bucket_name}/{formatted_files_prefix}/{fatalities_prefix}/",
                                ),
                            ]
                        ),
                        )
