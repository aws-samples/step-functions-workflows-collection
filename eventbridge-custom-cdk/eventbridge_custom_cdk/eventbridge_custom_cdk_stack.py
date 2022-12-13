from aws_cdk import (
    # Duration,
    Stack,
    RemovalPolicy,
    aws_events as events_,
    aws_sqs as sqs_,
    aws_iam as iam_,
    aws_sns as sns_,
    aws_logs as logs_,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn_,
    aws_events_targets as targets_)
from constructs import Construct

_project_name = "sample-stepfunctions-events"


class EventbridgeCustomCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create the SQS Target
        self.queue = sqs_.Queue(self,
                                "SQSQueue",
                                queue_name=f"{_project_name}-queue")

        #Create the SNS target
        self.topic = sns_.Topic(
            self,
            "SNSTopic",
            topic_name=f"{_project_name}-topic",
        )

        # Create the lambda function
        handler_code = ""
        with open("./src/handler.py", encoding="utf8") as fp:
            handler_code = fp.read()

        self.lambdaFn = lambda_.Function(
            self,
            "LambdaFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.InlineCode(handler_code),
            handler="index.handler",
            function_name=f"{_project_name}-Function",
        )

        #Create the lambda CW Log for retention and deletion
        logs_.LogGroup(
            self,
            "FunctionLogGroup",
            log_group_name=f"/aws/lambda/{self.lambdaFn.function_name}",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs_.RetentionDays.ONE_DAY,
        )

        # Create the EventBridge Bus to receive the custom event
        self.bus = events_.EventBus(self,
                                    "EventBridgeEventBus",
                                    event_bus_name=f"{_project_name}-eventbus")

        self.rule = events_.Rule(self,
                                 "EventBridgeRule",
                                 description="Step Function Output Rule",
                                 event_bus=self.bus,
                                 event_pattern=events_.EventPattern(
                                     detail_type=["MessageFromStepFunctions"],
                                     source=["my.statemachine"]),
                                 targets=[
                                     targets_.LambdaFunction(self.lambdaFn),
                                     targets_.SqsQueue(self.queue),
                                     targets_.SnsTopic(self.topic)
                                 ])

        #Create the State Machine and related resources

        # Execution Role
        self.sfn_role = iam_.Role(
            self,
            "StepFunctionExecRole",
            description="Allows AWS Batch submissions and Lambda Execution",
            assumed_by=iam_.ServicePrincipal("states.amazonaws.com"),
        )

        #read in the asl definition
        sfn_def = ""
        with open("./statemachine/statemachine.asl.json",
                  encoding="utf8") as fp:
            sfn_def = fp.read()

        self.sfn = sfn_.CfnStateMachine(
            self,
            "stateMachine",
            definition_string=sfn_def,
            definition_substitutions={"bus_name": self.bus.event_bus_name},
            state_machine_name=f"{_project_name}-statemachine",
            role_arn=self.sfn_role.role_arn)

        # Allow State Machine to put events on the Bus
        self.bus.grant_put_events_to(self.sfn_role)

        # Allow EventBridge to invoke Lambda
        self.lambdaFn.add_permission(
            "EbInvoke",
            principal=iam_.ServicePrincipal("events.amazonaws.com"),
            action="lambda:invoke",
            source_arn=self.rule.rule_arn)

        #Allow EventBridge to publish SQS Message
        self.queue.add_to_resource_policy(
            iam_.PolicyStatement(
                actions=["sqs:SendMessage"],
                conditions={
                    "ArnEquals": {
                        "aws:SourceArn": self.rule.rule_arn
                    }
                },
                principals=[iam_.ServicePrincipal("events.amazonaws.com")]))

        # Allow Eventbridge to publish SNS Message
        self.topic.add_to_resource_policy(
            iam_.PolicyStatement(
                actions=["sns:Publish"],
                principals=[iam_.ServicePrincipal("events.amazonaws.com")]))
