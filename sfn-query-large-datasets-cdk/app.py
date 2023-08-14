#!/usr/bin/env python3
import json
import random
import string
import os
from aws_cdk import (
    App,
    Environment,
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
    aws_iam as iam,
    aws_sns as sns,
    aws_kms as kms,
    aws_glue as glue,
    aws_athena as athena,
    aws_stepfunctions as sfn,
    CfnOutput as outputs
)
from constructs import Construct

class SfnQueryLargeDatasetsCdkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Random string generation for suffixes
        random_string = "".join(random.choices(string.ascii_lowercase, k=8))

        # S3 Bucket
        s3_bucket = s3.Bucket(self, "s3_query_large_datasets", 
            bucket_name=f"stepfunctions-query-large-datasets-{random_string}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # SNS KMS key
        sns_key = kms.Alias.from_alias_name(self, "SnsKey", "alias/aws/sns")

        # SNS Topic
        athena_updates_topic = sns.Topic(self, "athena_updates",
            topic_name="athena-updates-topic",
            master_key=sns_key,
        )

        # Glue IAM Role
        glue_crawler_role = iam.Role(self, "glue_crawler_role",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")
            ],
            role_name=f"glue-crawler-role-{random_string}",
        )

        # Glue Database
        glue_db = glue.CfnDatabase(self, "query_large_datasets_db",
            catalog_id=os.environ["CDK_DEFAULT_ACCOUNT"],
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                create_table_default_permissions=[
                    glue.CfnDatabase.PrincipalPrivilegesProperty(
                        permissions=["ALL"],
                        principal=glue.CfnDatabase.DataLakePrincipalProperty(
                            data_lake_principal_identifier="IAM_ALLOWED_PRINCIPALS"
                        )
                    )],
                description="Database for large datasets",
                name=f"query_large_datasets_db_{random_string}"
            )
        )

        # Crawler configuration
        crawler_configuration = {
            'Version': 1.0,
            'CrawlerOutput': {
                'Partitions': {'AddOrUpdateBehavior': 'InheritFromTable'}
            },
            'Grouping': {
                'TableGroupingPolicy': 'CombineCompatibleSchemas'}
        }

        # Glue Crawler
        glue_crawler = glue.CfnCrawler(self, "start_athena_crawler",
            database_name=glue_db.database_input.name,
            name=f"query_large_datasets_crawler-{random_string}",
            role=glue_crawler_role.role_arn,
            targets=glue.CfnCrawler.TargetsProperty(s3_targets=[glue.CfnCrawler.S3TargetProperty(path="s3://aws-glue-datasets-us-east-1/examples/githubarchive/month/data/")]),
            configuration=json.dumps(crawler_configuration),
        )
        glue_crawler.add_dependency(glue_db)


        # Athena Workgroup
        athena_workgroup = athena.CfnWorkGroup(self, "workgroup_start_athena",
            name=f"log-{random_string}",
            state="ENABLED",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{s3_bucket.bucket_name}/result/")
            )
        )
        athena_workgroup.apply_removal_policy(RemovalPolicy.DESTROY)


        # IAM Roles and Policies for Step Functions
        state_machine_role = iam.Role(self, "state_machine_role",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            role_name=f"query-large-datasets-{random_string}",
        )


        # IAM Policy
        athena_workflow_policy = iam.Policy(self, "athena_workflow_policy",
            policy_name=f"sfn-start-athena-policy-{random_string}",
            statements=[
                iam.PolicyStatement(
                    actions=["sns:Publish"],
                    resources=[athena_updates_topic.topic_arn],
                    effect=iam.Effect.ALLOW
                ),
                iam.PolicyStatement(
                    actions=[
                        "athena:getQueryResults",
                        "athena:startQueryExecution",
                        "athena:stopQueryExecution",
                        "athena:getQueryExecution",
                        "athena:getDataCatalog"
                    ],
                    resources=[
                        f"arn:aws:athena:{self.region}:{self.account}:workgroup/{athena_workgroup.name}",
                        f"arn:aws:glue:{self.region}:{self.account}:database/{glue_db.database_input.name}",
                    ],
                    effect=iam.Effect.ALLOW
                ),
                iam.PolicyStatement(
                    actions=[
                        "s3:GetBucketLocation",
                        "s3:GetObject",
                        "s3:ListBucket",
                        "s3:ListBucketMultipartUploads",
                        "s3:ListMultipartUploadParts",
                        "s3:AbortMultipartUpload",
                        "s3:CreateBucket",
                        "s3:PutObject"
                    ],
                    resources=["arn:aws:s3:::*"],
                    effect=iam.Effect.ALLOW
                ),
                iam.PolicyStatement(
                    actions=[
                        "glue:CreateDatabase",
                        "glue:GetDatabase",
                        "glue:GetDatabases",
                        "glue:UpdateDatabase",
                        "glue:DeleteDatabase",
                        "glue:CreateTable",
                        "glue:UpdateTable",
                        "glue:GetTable",
                        "glue:GetTables",
                        "glue:DeleteTable",
                        "glue:BatchDeleteTable",
                        "glue:BatchCreatePartition",
                        "glue:CreatePartition",
                        "glue:UpdatePartition",
                        "glue:GetPartition",
                        "glue:GetPartitions",
                        "glue:BatchGetPartition",
                        "glue:DeletePartition",
                        "glue:BatchDeletePartition",
                        "glue:StartCrawler",
                        "glue:GetCrawler"
                    ],
                    resources=[
                        f"arn:aws:glue:{self.region}:{self.account}:catalog",
                        f"arn:aws:glue:{self.region}:{self.account}:database/*",
                        f"arn:aws:glue:{self.region}:{self.account}:table/*/*",
                        f"arn:aws:glue:{self.region}:{self.account}:crawler/*"
                    ],
                    effect=iam.Effect.ALLOW
                )
            ]
        )

        state_machine_role.attach_inline_policy(athena_workflow_policy)


        # Step Functions State Machine Definition
        state_machine_definition = ""
        with open("./statemachine/statemachine.asl.json", encoding="utf8") as file_read:
            state_machine_definition = file_read.read()


        # Step Functions State Machine
        sfn_state_machine = sfn.CfnStateMachine(self, "sfn_athena",
            state_machine_name=f"state-machine-start-athena-{random_string}",
            role_arn=state_machine_role.role_arn,
            definition_string=state_machine_definition,
            definition_substitutions={
                "aws_athena_workgroup": athena_workgroup.name,
                "query_large_datasets_db": glue_db.database_input.name,
                "topic_athena_updates": athena_updates_topic.topic_arn,
                "glue_crawler_name": glue_crawler.name,
            },
        )


        # CloudFormation Outputs
        outputs(self, "aws_sfn_state_machine", value=sfn_state_machine.ref)
        outputs(self, "bucket_domain_name", value=s3_bucket.bucket_domain_name)
        outputs(self, "aws_glue_crawler", value=glue_crawler.name)



# Launch the stack
app = App()

SfnQueryLargeDatasetsCdkStack(app, "SfnQueryLargeDatasets",
    env=Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */
    #env=cdk.Environment(account='123456789012', region='us-east-1'),
    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()
