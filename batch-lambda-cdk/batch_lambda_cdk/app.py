#!/usr/bin/env python3

from typing_extensions import Self
from aws_cdk import (
    App,
    Stack,
    RemovalPolicy,
    Duration,
    aws_batch as batch,
    aws_ec2 as ec2,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_iam as iam_

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
        self.batch_vpc = ec2.Vpc(self, "BatchVPC", cidr=vpc_cidr, max_azs=1,
                                 subnet_configuration=[ec2.SubnetConfiguration(subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24, map_public_ip_on_launch=True,
                                                                               name=resource_prefix)])
        _vpc_id = self.batch_vpc.vpc_id

        # get the first az for use later
        _az = self.batch_vpc.availability_zones[0]

        # create the public route table
        self.public_route_table = ec2.CfnRouteTable(
            self, "PublicRouteTable", vpc_id=_vpc_id)

        # Create a security group for the batch environment
        self.batch_sg = ec2.CfnSecurityGroup(self, "BatchSecurityGroup", group_name=resource_prefix+"-sg",
                                             vpc_id=_vpc_id, group_description="SG for AWS Batch")

        # Create the lambda function

        with open("./lambda-handler.py", encoding="utf8") as fp:
            handler_code = fp.read()

        lambdaFn = lambda_.Function(self, "GenerateBatchJobMap",
                                    runtime=lambda_.Runtime.PYTHON_3_9,
                                    code=lambda_.InlineCode(handler_code),
                                    handler="index.handler",
                                    function_name=f"{resource_prefix}-Function"

                                    )

        # Create the log group seperately for retention period and deletion upon cleanup
        logs.LogGroup(
            self,
            'FunctionLogGroup',
            log_group_name=f"/aws/lambda/{lambdaFn.function_name}",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.ONE_DAY
        )

        # Build the AWS Batch Compute Environment
        # Create the Service Role for Batch
        self.batch_exec_role = iam_.Role(self, "BatchJobWithLambdaExecutionRole",
                                         description="Allows AWS Batch submissions and Lambda Execution",
                                         assumed_by=iam_.ServicePrincipal("states.amazonaws.com"))
        # add the policies to the role
        self.batch_exec_role.add_to_policy(
            iam_.PolicyStatement(actions=['batch:SubmitJob', 'batch:DescribeJobs', 'batch.TerminateJob'],
                                 effect=iam_.Effect.Allow, resources=["*"])
        )
        self.batch_exec_role.add_to_policy(
            iam_.PolicyStatement(actions=["lambda.InvokeFunction"],
                                 effect=iam_.Effect.Allow,
                                 resources=[lambdaFn.function_arn])

        )


app = App()
BatchLambdaCdkStack(app, "BatchLambdaCdkStack")

app.synth()
