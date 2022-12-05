#!/usr/bin/env python3


from aws_cdk import (
    App,
    Stack,
    Environment as env_,
    RemovalPolicy,
    Duration,
    aws_batch as batch,
    aws_ec2 as ec2,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_iam as iam_,
    aws_stepfunctions as stepfunctions,
    CfnOutput as outputs,
)
import os
from constructs import Construct


class BatchLambdaCdkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # A few common variables
        vpc_cidr = "10.0.0.0/16"

        resource_prefix = "sfn-batch-sample"

        # Create the VPC and VPC-related resources for AWS Batch
        # batch_vpc will create the VPC, IGW, and a single public subnet.
        self.batch_vpc = ec2.Vpc(
            self,
            "BatchVPC",
            cidr=vpc_cidr,
            max_azs=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                    map_public_ip_on_launch=True,
                    name=resource_prefix,
                )
            ],
        )
        _vpc_id = self.batch_vpc.vpc_id

        # get the first az for use later
        _az = self.batch_vpc.availability_zones[0]

        # create the public route table
        self.public_route_table = ec2.CfnRouteTable(
            self, "PublicRouteTable", vpc_id=_vpc_id
        )

        # Create a security group for the batch environment
        self.batch_sg = ec2.SecurityGroup(
            self,
            "BatchSecurityGroup",
            security_group_name=resource_prefix + "-sg",
            vpc=self.batch_vpc,
            description="SG for AWS Batch",
        )
        # Create the lambda function

        with open("./lambda-handler.py", encoding="utf8") as fp:
            handler_code = fp.read()

        self.lambdaFn = lambda_.Function(
            self,
            "GenerateBatchJobMap",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.InlineCode(handler_code),
            handler="index.handler",
            function_name=f"{resource_prefix}-Function",
        )

        # Create the log group seperately for retention period and deletion upon cleanup
        logs.LogGroup(
            self,
            "FunctionLogGroup",
            log_group_name=f"/aws/lambda/{self.lambdaFn.function_name}",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.ONE_DAY,
        )

        # Build the AWS Batch Compute Environment
        # Create the Service Role for Batch
        self.sfn_exec_batch_role = iam_.Role(
            self,
            "BatchJobWithLambdaExecutionRole",
            description="Allows AWS Batch submissions and Lambda Execution",
            assumed_by=iam_.ServicePrincipal("states.amazonaws.com"),
        )
        # add the policies to the role
        self.sfn_exec_batch_role.add_to_policy(
            iam_.PolicyStatement(
                actions=["batch:SubmitJob", "batch:DescribeJobs", "batch:TerminateJob"],
                effect=iam_.Effect.ALLOW,
                resources=["*"],
            )
        )
        self.sfn_exec_batch_role.add_to_policy(
            iam_.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                effect=iam_.Effect.ALLOW,
                resources=[self.lambdaFn.function_arn],
            )
        )

        self.sfn_exec_batch_role.add_to_policy(
            iam_.PolicyStatement(
                actions=["events:PutTargets", "events:PutRule", "events:DescribeRule"],
                effect=iam_.Effect.ALLOW,
                resources=[
                    f"arn:aws:events:{self.region}:{self.account}:rule/StepFunctionsGetEventsForBatchJobsRule"
                ],
            )
        )

        # Create the ECS Instance Role
        self.ecs_role = iam_.Role(
            self,
            "BatchEcsInstanceRole",
            description="ECS Role",
            assumed_by=iam_.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam_.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonEC2ContainerServiceforEC2Role"
                )
            ],
        )

        # Create the ECS instance profile and attach to the ECS Role
        self.ecs_profile = iam_.CfnInstanceProfile(
            self, "BatchIamInstanceProfile", roles=[self.ecs_role.role_name]
        )

        # Create the Batch compute environment

        self.subnets = self.batch_vpc.select_subnets(
            subnet_type=ec2.SubnetType.PUBLIC
        ).subnet_ids

        self.batch_role = iam_.Role(
            self,
            "BatchAWSBatchServiceRole",
            description="Batch Role",
            assumed_by=iam_.ServicePrincipal("batch.amazonaws.com"),
            managed_policies=[
                iam_.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSBatchServiceRole"
                )
            ],
        )

        self.batch_env = batch.CfnComputeEnvironment(
            self,
            "BatchComputeEnvironment",
            compute_environment_name=f"{resource_prefix}-Compute",
            type="MANAGED",
            service_role=self.batch_role.role_arn,
            compute_resources=batch.CfnComputeEnvironment.ComputeResourcesProperty(
                maxv_cpus=64,
                subnets=self.subnets,
                type="EC2",
                minv_cpus=0,
                desiredv_cpus=0,
                instance_role=self.ecs_profile.attr_arn,
                instance_types=["optimal"],
                security_group_ids=[self.batch_sg.security_group_id],
            ),
        )
        # Create the batch queue
        self.queue = batch.CfnJobQueue(
            self,
            "BatchJobQueue",
            compute_environment_order=[
                batch.CfnJobQueue.ComputeEnvironmentOrderProperty(
                    compute_environment=self.batch_env.attr_compute_environment_arn,
                    order=1,
                )
            ],
            priority=1,
        )

        # Create the job definition which will be triggered by the Step Function
        self.batch_def = batch.CfnJobDefinition(
            self,
            "BatchJobDefinition",
            type="container",
            job_definition_name=resource_prefix + "-job",
            container_properties=batch.CfnJobDefinition.ContainerPropertiesProperty(
                image=f"137112412989.dkr.ecr.{self.region}.amazonaws.com/amazonlinux:latest",
                command=["echo", "Ref::input"],
                memory=2000,
                vcpus=2,
            ),
            retry_strategy=batch.CfnJobDefinition.RetryStrategyProperty(attempts=1),
        )

        # Create the state machine which invokes the Lambda function and runs a batch job.  This
        # uses the CfnStatemachine construct to enable easy import of an asl file as the definition

        self.state_machine_def = self.read_statemachine_definition(
            filepath="statemachine/statemachine.asl.json"
        )

        self.state_machine = stepfunctions.CfnStateMachine(
            self,
            "BatchJobWithLambdaStateMachine",
            role_arn=self.sfn_exec_batch_role.role_arn,
            definition_string=self.state_machine_def,
            definition_substitutions={
                "GenerateBatchJobArn": self.lambdaFn.function_arn,
                "jobQueueArn": self.queue.attr_job_queue_arn,
                "jobDefinitionArn": self.batch_def.ref,
            },
            state_machine_name=resource_prefix + "-sfn-cdk",
        )

        # Cloudformation outputs to the terminal
        self.sfn_name = outputs(
            self, "StateMachineName", value=self.state_machine.attr_name
        )

        self.sfn_arn = outputs(
            self, "StatemachineArn", value=self.state_machine.attr_arn
        )

    def read_statemachine_definition(self, filepath: str):

        read_file = open(filepath, "rt")
        file_contents = read_file.read()
        read_file.close()
        return file_contents


app = App()
BatchLambdaCdkStack(app, "BatchLambdaCdkStack")

app.synth()
