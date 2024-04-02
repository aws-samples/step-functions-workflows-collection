#!/usr/bin/env python3
import os

import aws_cdk as cdk

from sfn_migrate_rds_to_aurora_postgres_workflow_cdk.sfn_migrate_rds_to_aurora_postgres_workflow_cdk_stack import SfnMigrateRdsToAuroraPostgresWorkflowCdkStack


app = cdk.App()
SfnMigrateRdsToAuroraPostgresWorkflowCdkStack(app, "SfnMigrateRdsToAuroraPostgresWorkflowCdkStack",
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.

    #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */

    #env=cdk.Environment(account='123456789012', region='us-east-1'),

    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()
