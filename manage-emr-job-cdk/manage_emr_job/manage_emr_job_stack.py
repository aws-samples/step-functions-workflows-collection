from constructs import Construct
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_s3 as s3,
)


class ManageEmrJobStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        s3_logging_bucket = s3.Bucket(
            self,
            "EMRLogS3Bucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        emr_service_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "iam:CreateServiceLinkedRole",
                "iam:PutRolePolicy"
            ],
            resources=[f"arn:{self.partition}:iam::*:role/aws-service-role/elasticmapreduce.amazonaws.com*/AWSServiceRoleForEMRCleanup*"],
            conditions={"StringLike": {"iam:AWSServiceName": "elasticmapreduce.amazonaws.com"}}
        )

        emr_service_role = iam.Role(
            self,
            "EMRServiceRole",
            assumed_by=iam.ServicePrincipal("elasticmapreduce.amazonaws.com"),
            inline_policies={
                "AllowServiceLinkedRole": iam.PolicyDocument(
                    statements=[
                        emr_service_policy
                    ]
                )
            },
        )

        emr_service_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:AuthorizeSecurityGroupEgress",
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:CancelSpotInstanceRequests",
                    "ec2:CreateFleet",
                    "ec2:CreateLaunchTemplate",
                    "ec2:CreateNetworkInterface",
                    "ec2:CreateSecurityGroup",
                    "ec2:CreateTags",
                    "ec2:DeleteLaunchTemplate",
                    "ec2:DeleteNetworkInterface",
                    "ec2:DeleteSecurityGroup",
                    "ec2:DeleteTags",
                    "ec2:DescribeAvailabilityZones",
                    "ec2:DescribeAccountAttributes",
                    "ec2:DescribeDhcpOptions",
                    "ec2:DescribeImages",
                    "ec2:DescribeInstanceStatus",
                    "ec2:DescribeInstances",
                    "ec2:DescribeKeyPairs",
                    "ec2:DescribeLaunchTemplates",
                    "ec2:DescribeNetworkAcls",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribePrefixLists",
                    "ec2:DescribeRouteTables",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeSpotInstanceRequests",
                    "ec2:DescribeSpotPriceHistory",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeTags",
                    "ec2:DescribeVpcAttribute",
                    "ec2:DescribeVpcEndpoints",
                    "ec2:DescribeVpcEndpointServices",
                    "ec2:DescribeVpcs",
                    "ec2:DetachNetworkInterface",
                    "ec2:ModifyImageAttribute",
                    "ec2:ModifyInstanceAttribute",
                    "ec2:RequestSpotInstances",
                    "ec2:RevokeSecurityGroupEgress",
                    "ec2:RunInstances",
                    "ec2:TerminateInstances",
                    "ec2:DeleteVolume",
                    "ec2:DescribeVolumeStatus",
                    "ec2:DescribeVolumes",
                    "ec2:DetachVolume",
                    "iam:GetRole",
                    "iam:GetRolePolicy",
                    "iam:ListInstanceProfiles",
                    "iam:ListRolePolicies",
                    "iam:PassRole",
                    "s3:CreateBucket",
                    "s3:Get*",
                    "s3:List*",
                    "sdb:BatchPutAttributes",
                    "sdb:Select",
                    "sqs:CreateQueue",
                    "sqs:Delete*",
                    "sqs:GetQueue*",
                    "sqs:PurgeQueue",
                    "sqs:ReceiveMessage",
                    "cloudwatch:PutMetricAlarm",
                    "cloudwatch:DescribeAlarms",
                    "cloudwatch:DeleteAlarms",
                    "application-autoscaling:RegisterScalableTarget",
                    "application-autoscaling:DeregisterScalableTarget",
                    "application-autoscaling:PutScalingPolicy",
                    "application-autoscaling:DeleteScalingPolicy",
                    "application-autoscaling:Describe*"
                ],
                resources=["*"],
            ),
        )
        
        emr_ec2_role_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            resources=[s3_logging_bucket.bucket_arn],
        )

        emr_ec2_role = iam.Role(
            self,
            "EMREc2Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            inline_policies={
                "emr-job-flow-role-policies": iam.PolicyDocument(
                    statements=[
                        emr_ec2_role_policy
                    ]
                )
            },
        )

        emr_ec2_instance_profile = iam.CfnInstanceProfile(
            self,
            "EMREc2InstanceProfile",
            path="/",
            roles=[emr_ec2_role.role_name],
        )

        sfn_execution_role = iam.Role(
            self,
            "EMRJobManagerStateMachineExecutionRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            inline_policies={
                "AllowServiceLinkedRole": iam.PolicyDocument(
                    statements=[
                        emr_service_policy
                    ]
                )
            },
        )

        sfn_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "elasticmapreduce:RunJobFlow",
                    "elasticmapreduce:TerminateJobFlows",
                    "elasticmapreduce:DescribeCluster",
                    "elasticmapreduce:AddJobFlowSteps",
                    "elasticmapreduce:DescribeStep"
                ],
                resources=["*"],
            ),
        )

        sfn_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "iam:PassRole"
                ],
                resources=[emr_service_role.role_arn, emr_ec2_role.role_arn],
            ),
        )

        state_machine_definition = ""
        with open("./statemachine/statemachine.asl.json", encoding="utf8") as file_read:
            state_machine_definition = file_read.read()

        state_machine = sfn.CfnStateMachine(
            self,
            "EMRJobManagerStateMachine",
            role_arn=sfn_execution_role.role_arn,
            definition_string=state_machine_definition,
            definition_substitutions={
                "Partition": self.partition,
                "emrServiceRole": emr_service_role.role_name,
                "emrEc2InstanceProfile": emr_ec2_instance_profile.ref,
                "emrS3LogBucket": s3_logging_bucket.bucket_name,
                "commandArguments1": "bash",
                "commandArguments2": "-c",
                "commandArguments3": "ls",
            },
        )

        CfnOutput(
            self,
            "oStateMachineArn",
            value=state_machine.attr_arn,
        )
