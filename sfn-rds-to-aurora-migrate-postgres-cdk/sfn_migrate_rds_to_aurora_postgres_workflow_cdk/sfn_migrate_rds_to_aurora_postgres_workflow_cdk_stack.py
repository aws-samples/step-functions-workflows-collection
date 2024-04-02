from aws_cdk import (
    Duration,
    Stack,
    CfnOutput,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
)
from constructs import Construct

class SfnMigrateRdsToAuroraPostgresWorkflowCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ##########################################################################
        #   Step Functions State Machine                                         #
        ##########################################################################

        sfn_comment = '''
        This State Machine workflow converts an RDS PostgreSQL (R-PgSQL) DB instance to an Aurora PostgreSQL (A-PgSQL) DB Cluster by migrating the data from one to another. 
        The workflow is divided into the following states: 
        1/ create a snapshot of the R-PgSQL instance, 
        2/ restore an A-PgSQL Cluster using this snapshot 
        3/ create an instance of A-PgSQL inside the cluster. 

        The final RDS snapshot will be named "{rds-instance-name}-final-snapshot". 
        The A-PgSQL Cluster will be named "{rds-instance-name}-apg-cluster"
        The Primary node in the A-PgSQL cluster will be named "{rds-instance-name}-apg-instance-1"

        The SFN needs the following input to be provided:
        Input Params: 
        {
            "dbInstanceId": "<name of R-PgSQL instance to convert to A-PgSQL cluster>",
            "dbInstanceClass": "<The compute and memory capacity of the A-PgSQL DB instance that will be created, for example db.m5.large>",
            "alsoUpgradeTo": "<Optional - if supplied, the version to try to upgrade A-PgSQL instance to after migrating>"
        }
        '''

        # Fail state - to catch errors and exit
        fail_state = sfn.Fail(self, "Fail",
                              cause_path="$.output.Cause",
                              error_path="$.output.Error"
        )

        # Success state - indicates state machine has existed successfully
        success_state = sfn.Succeed(self, "Success",
                                    comment="Migration to Aurora Postgres complete"
        )
                                    
        # Task - RDS:DescribeDbInstances
        # This task will be used to get the DB Engine Version details & the DB Instance Class of the provided dbInstanceId
        describe_db_instances_task = sfn_tasks.CallAwsService(self, "Describe DB Instances",
                                                              service="rds",
                                                              action="describeDBInstances",
                                                              iam_resources=["*"],
                                                              parameters={
                                                                "DbInstanceIdentifier.$": "$.dbInstanceId"
                                                              },
                                                              result_selector={
                                                                "EngineVersion.$": "$.DbInstances[0].EngineVersion",
                                                                "Engine.$": "$.DbInstances[0].Engine",
                                                                "DbInstanceClass.$": "$.DbInstances[0].DbInstanceClass"
                                                              },
                                                              result_path="$.VersionDetails"
        )

        # Task - RDS:CreateDBSnapshot
        # This task will be used to create the final snapshot of the provided RDS DB instance
        # if the RDS DB instance has any tags, then those tags are also copied to the snapshots. 
        # in that case, the additional_iam_statements parameter is used to add the rds:AddTagsToResource permission.
        create_final_snapshot_task = sfn_tasks.CallAwsService(self, "Create Final Snapshot",
                                                              service="rds",
                                                              action="createDBSnapshot",
                                                              iam_resources=["*"],
                                                              additional_iam_statements=[
                                                                  iam.PolicyStatement(
                                                                      actions=["rds:AddTagsToResource"],
                                                                      resources=["*"]
                                                                    )
                                                              ],
                                                              parameters={
                                                                "DbInstanceIdentifier.$": "$.dbInstanceId",
                                                                "DbSnapshotIdentifier.$": "States.Format('{}-final-snapshot', $.dbInstanceId)"
                                                              },
                                                              result_selector={
                                                                "DbSnapshotStatus.$": "$.DbSnapshot.Status",
                                                                "DbSnapshotArn.$": "$.DbSnapshot.DbSnapshotArn",
                                                                "DbSnapshotIdentifier.$": "$.DbSnapshot.DbSnapshotIdentifier"
                                                              },
                                                              result_path="$.DbSnapshot"
        )
        
        # Add a catch to the create final snapshot task to fail the workflow if there is an error
        create_final_snapshot_task.add_catch(fail_state, errors=["States.ALL"], result_path="$.output")

        # Add a wait state to wait for the snapshot to be available
        creating_snapshot_wait_x = sfn.Wait(self, "Creating Snapshot - WaitX",
                                   state_name = "Creating Snapshot, Wait 30s",
                                   time=sfn.WaitTime.duration(Duration.seconds(30))
        )

        # Task - RDS:DescribeDBSnapshots
        # This task will be used to check if the snapshot is available
        check_db_snapshot_status_task = sfn_tasks.CallAwsService(self, "Check DBSnapshot Status",
                                                              service="rds",
                                                              action="describeDBSnapshots",
                                                              iam_resources=["*"],
                                                              parameters={
                                                                "DbSnapshotIdentifier.$": "$.DbSnapshot.DbSnapshotIdentifier"
                                                              },
                                                              result_selector={
                                                                "DbSnapshotStatus.$": "$.DbSnapshots[0].Status",
                                                                "DbSnapshotArn.$": "$.DbSnapshots[0].DbSnapshotArn",
                                                                "DbSnapshotIdentifier.$": "$.DbSnapshots[0].DbSnapshotIdentifier"
                                                              },
                                                              result_path="$.DbSnapshot"
        )

        # Task - RDS:RestoreDBClusterFromSnapshot
        # This task will be used to restore a (i.e create new) Aurora Cluster using the snapshot
        restore_db_cluster_from_snapshot_task = sfn_tasks.CallAwsService(self, "Restore DBCluster from Snapshot",
                                                                         service="rds",
                                                                         action="restoreDBClusterFromSnapshot",
                                                                         iam_resources=["*"],
                                                                         parameters={
                                                                             "DbClusterIdentifier.$": "States.Format('{}-apg-cluster', $.dbInstanceId)",
                                                                             "Engine": "aurora-postgresql",
                                                                             "EngineVersion.$": "$.VersionDetails.EngineVersion",
                                                                             "SnapshotIdentifier.$": "$.DbSnapshot.DbSnapshotArn"
                                                                         },
                                                                         result_selector={
                                                                            "DbClusterIdentifier.$": "$.DbCluster.DbClusterIdentifier"
                                                                         },
                                                                         result_path="$.AuroraClusterDetails"
        )

        # Add a catch to the restore db cluster from snapshot task to fail the workflow if there is an error
        restore_db_cluster_from_snapshot_task.add_catch(fail_state, errors=["States.ALL"], result_path="$.output")
        
        # Add a wait state to wait for the Aurora Cluster to be available
        creating_aurora_cluster_wait_x = sfn.Wait(self, "ClusterRestoring - Wait 30s",
                                   state_name = "ClusterRestoring - Wait 30s",
                                   time=sfn.WaitTime.duration(Duration.seconds(30))
        )

        # Task - RDS:DescribeDBClusters
        # This task will be used to check if the Aurora Cluster is available
        check_aurora_cluster_status_task = sfn_tasks.CallAwsService(self, "DescribeDBClusters",
                                                              service="rds",
                                                              action="describeDBClusters",
                                                              iam_resources=["*"],
                                                              parameters={
                                                                "DbClusterIdentifier.$": "$.AuroraClusterDetails.DbClusterIdentifier"
                                                              },
                                                              result_selector={
                                                                "DbClusterStatus.$": "$.DbClusters[0].Status",
                                                                "DbClusterIdentifier.$": "$.DbClusters[0].DbClusterIdentifier"
                                                              },
                                                              result_path="$.AuroraClusterDetails"
        )

        # Task - RDS:CreateDBInstance
        # This task will be used to create an instance of the Aurora Cluster
        create_aurora_instance_task = sfn_tasks.CallAwsService(self, "Create Aurora Instance",
                                                               service="rds",
                                                               action="createDBInstance",
                                                               iam_resources=["*"],
                                                               parameters={
                                                                   "DbClusterIdentifier.$": "$.AuroraClusterDetails.DbClusterIdentifier",
                                                                   "DbInstanceIdentifier.$": "States.Format('{}-apg-instance-1', $.dbInstanceId)",
                                                                   "DbInstanceClass.$": "$.dbInstanceClass",
                                                                   "Engine": "aurora-postgresql"
                                                               },
                                                               result_selector={
                                                                   "DbInstanceStatus.$": "$.DbInstance.DbInstanceStatus",
                                                                   "DbInstanceIdentifier.$": "$.DbInstance.DbInstanceIdentifier"
                                                               },
                                                               result_path="$.AuroraClusterDetails"
        )
        
        # Add a catch to the create aurora instance task to fail the workflow if there is an error
        create_aurora_instance_task.add_catch(fail_state, errors=["States.ALL"], result_path="$.output")
        
        # Add a wait state to wait for the Aurora Instance to be available
        creating_aurora_instance_wait_x = sfn.Wait(self, "ClusterInstance Creating - Wait 30s",
                                   state_name = "ClusterInstance Creating - Wait 30s",
                                   time=sfn.WaitTime.duration(Duration.seconds(30))
        )

        # Task - RDS:DescribeDBInstances
        # This task will be used to check if the Aurora Instance is available
        check_aurora_instance_status_task = sfn_tasks.CallAwsService(self, "DescribeDBInstances",
                                                              service="rds",
                                                              action="describeDBInstances",
                                                              iam_resources=["*"],
                                                              parameters={
                                                                "DbInstanceIdentifier.$": "$.AuroraClusterDetails.DbInstanceIdentifier"
                                                              },
                                                              result_selector={
                                                                "DbInstanceStatus.$": "$.DbInstances[0].DbInstanceStatus",
                                                                "DbInstanceIdentifier.$": "$.DbInstances[0].DbInstanceIdentifier",
                                                                "DbClusterIdentifier.$": "$.DbInstances[0].DbClusterIdentifier"
                                                              },
                                                              result_path="$.AuroraClusterDetails"
        )

        # Task - RDS:ModifyDBCluster
        # This task will be used to modify the Aurora Cluster to upgrade to a newer version
        modify_aurora_cluster_task = sfn_tasks.CallAwsService(self, "Modify Aurora Cluster",
                                                               service="rds",
                                                               action="modifyDBCluster",
                                                               iam_resources=["*"],
                                                               parameters={
                                                                   "DbClusterIdentifier.$": "$.AuroraClusterDetails.DbClusterIdentifier",
                                                                   "EngineVersion.$": "$.alsoUpgradeTo",
                                                                   "AllowMajorVersionUpgrade": True,
                                                                   "ApplyImmediately": True
                                                               },
                                                               result_selector={
                                                                   "DbClusterStatus.$": "$.DbCluster.Status",
                                                                   "DbClusterIdentifier.$": "$.DbCluster.DbClusterIdentifier"
                                                               },
                                                               result_path="$.AuroraClusterDetails"
        )
        
        # Add a catch to the modify aurora cluster task to fail the workflow if there is an error
        modify_aurora_cluster_task.add_catch(fail_state, errors=["States.ALL"], result_path="$.output")

        # Chain of States
        create_aurora_instance_chain = create_aurora_instance_task.next(creating_aurora_instance_wait_x).next(check_aurora_instance_status_task).next(
            sfn.Choice(self, "Is Aurora Instance Ready?")
            .when(sfn.Condition.string_equals("$.AuroraClusterDetails.DbInstanceStatus", "available"), 
                    sfn.Choice(self, "AlsoUpgradeCluster?")
                        .when(sfn.Condition.is_present("$.alsoUpgradeTo"), modify_aurora_cluster_task.next(success_state))
                        .otherwise(success_state)
                )
            .otherwise(creating_aurora_instance_wait_x)
        )

        create_aurora_cluster_chain = restore_db_cluster_from_snapshot_task.next(creating_aurora_cluster_wait_x).next(check_aurora_cluster_status_task).next(
            sfn.Choice(self, "Is Aurora Cluster Ready?")
            .when(sfn.Condition.string_equals("$.AuroraClusterDetails.DbClusterStatus", "available"), create_aurora_instance_chain)
            .otherwise(creating_aurora_cluster_wait_x)
        )

        prepare_rds_snapshot_chain = describe_db_instances_task.next(create_final_snapshot_task).next(creating_snapshot_wait_x).next(check_db_snapshot_status_task).next(
            sfn.Choice(self, "Is DBSnapshot Available?")
            .when(sfn.Condition.string_equals("$.DbSnapshot.DbSnapshotStatus", "available"), create_aurora_cluster_chain)
            .otherwise(creating_snapshot_wait_x)
        )

        sfn_workflow = sfn.StateMachine(self, "rds-migrate-to-aurora-postgres-workflow",
                                        state_machine_name="rds-migrate-to-aurora-postgres-workflow",
                                        comment=sfn_comment,
                                        definition_body=sfn.DefinitionBody.from_chainable(prepare_rds_snapshot_chain)
        )

        CfnOutput(self, "SFName",
            value=sfn_workflow.state_machine_name, 
            export_name='SFNStateMachineName',
            description='Step Function Name')

        CfnOutput(self, "SFArn",
            value=sfn_workflow.state_machine_arn,
            export_name='SFNStateMachineArn',
            description='Step Function ARN')

