import aws_cdk as core
import aws_cdk.assertions as assertions

from sfn_migrate_rds_to_aurora_postgres_workflow_cdk.sfn_migrate_rds_to_aurora_postgres_workflow_cdk_stack import SfnMigrateRdsToAuroraPostgresWorkflowCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in sfn_migrate_rds_to_aurora_postgres_workflow_cdk/sfn_migrate_rds_to_aurora_postgres_workflow_cdk_stack.py
def test_sfn_rds_created():
    app = core.App()
    stack = SfnMigrateRdsToAuroraPostgresWorkflowCdkStack(app, "sfn-migrate-rds-to-aurora-postgres-workflow-cdk")
    template = assertions.Template.from_stack(stack)
