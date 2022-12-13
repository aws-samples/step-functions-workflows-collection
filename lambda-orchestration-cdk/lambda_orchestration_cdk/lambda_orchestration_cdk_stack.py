from aws_cdk import (
    Duration,
    Stack,
    aws_iam as iam_,
    aws_sqs as sqs_,
    aws_lambda as _lambda,
    aws_logs as _logs,
    RemovalPolicy,
    aws_sns as _sns,
    aws_kms as _kms,
    aws_stepfunctions as _sfn,
    aws_lambda_event_sources as _les,
    CfnOutput as outputs_,
)
from constructs import Construct


class LambdaOrchestrationCdkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        resource_prefix = "sample-sfn-orchestrate-lambda"

        # This is the list of cookie-cutter lambda functions to be created.  We will
        # iterate through this list later to create the functions
        lambdaDefList = [
            {"srcName": "buy-sell-recommend.py", "fnName": "buy-sell-recommend"},
            {"srcName": "checkprice.py", "fnName": "check-price"},
            {"srcName": "buy.py", "fnName": "buy"},
            {"srcName": "sell.py", "fnName": "sell"},
        ]

        # Create a single Lambda role to execute most functions since they only generate random data
        self.lambdaRole = iam_.Role(
            self,
            "FunctionRole",
            assumed_by=iam_.ServicePrincipal("lambda.amazonaws.com"),
            description="Lambda execution role",
            managed_policies=[
                iam_.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        self.lambdaList = {}  # this holds references to each created lambda function
        for l in lambdaDefList:

            handler_code = ""
            with open(
                f"lambda_orchestration_cdk/src/{l['srcName']}", encoding="utf8"
            ) as fp:
                handler_code = fp.read()

            # Create the current lambda function
            t = _lambda.Function(
                self,
                l["fnName"],
                code=_lambda.InlineCode(handler_code),
                handler="index.handler",
                runtime=_lambda.Runtime.PYTHON_3_9,
                role=self.lambdaRole,
                function_name=f"{resource_prefix}-{l['fnName']}",
            )
            # Add the reference to the list
            self.lambdaList[l["fnName"]] = t
            # create the CloudWatch log trail
            _logs.LogGroup(
                self,
                f"{l['fnName']}Log",
                removal_policy=RemovalPolicy.DESTROY,
                retention=_logs.RetentionDays.ONE_DAY,
                log_group_name=f"/aws/lambda/{resource_prefix}-{l['fnName']}",
            )

        # create a seperate role for the buy-sell-recommend function since it requires additional
        # privileges
        self.buySellRole = iam_.Role(
            self,
            "BuySellRole",
            assumed_by=iam_.ServicePrincipal("lambda.amazonaws.com"),
            description="Buy/Sell Lambda Role",
            managed_policies=[
                iam_.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Create the buy/sell function to notify the Step Function of the approval
        handler_code = ""
        with open("lambda_orchestration_cdk/src/buy-sell.py", encoding="utf8") as fp:
            handler_code = fp.read()

        self.buySellFunction = _lambda.Function(
            self,
            "BuySellFunction",
            handler="index.handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            role=self.buySellRole,
            code=_lambda.InlineCode(handler_code),
            description="Simulates buy/sell approval",
            function_name=f"{resource_prefix}-buy-sell-fn",
        )
        # explicitly create the CloudWatch Logs Logroup for retention and cleanup
        _logs.LogGroup(
            self,
            "BuySellFnLog",
            removal_policy=RemovalPolicy.DESTROY,
            retention=_logs.RetentionDays.ONE_DAY,
            log_group_name=f"/aws/lambda/{self.buySellFunction.function_name}",
        )

        # SQS Queue which simulates a trader accepting/rejecting the recommendation
        self.queue = sqs_.Queue(
            self,
            "RequestApprovalQueue",
            queue_name=f"{resource_prefix}-approvals",
            visibility_timeout=Duration.seconds(180),
        )
        # This allows the BuySell Lambda role to consume SQS messages
        self.queue.grant_consume_messages(self.buySellRole)

        # create the Lambda event source on the SQS Queue
        self.buySellFunction.add_event_source(_les.SqsEventSource(self.queue))

        # loop through the lambda list and create a new list for the resource block in a policy
        fn_arn_list = []
        for fn in self.lambdaList:
            fn_arn_list.append(self.lambdaList[fn].function_arn)

        # create the SFN execution role
        self.state_machine_role = iam_.Role(
            self,
            "StateMachineExecRole",
            assumed_by=iam_.ServicePrincipal("states.amazonaws.com"),
            description="Sample Stock Trade Step Function Role",
        )
        # attach an inline policy granting lambda invoke rights to the SFN
        self.state_machine_role.attach_inline_policy(
            iam_.Policy(
                self,
                "lambda-policy",
                statements=[
                    iam_.PolicyStatement(
                        actions=["lambda:Invoke*"],
                        effect=iam_.Effect.ALLOW,
                        resources=fn_arn_list,
                    )
                ],
            )
        )
        # import the default sns key
        sns_alias = _kms.Alias.from_alias_name(self, "key", "alias/aws/sns")
        # create the result sns topic and attach publishing rights to the SFN role
        self.topic = _sns.Topic(
            self,
            "AlertTopic",
            display_name="Buy-Sell-Results",
            master_key=sns_alias,
            topic_name=f"{resource_prefix}-Results",
        )
        self.topic.grant_publish(self.state_machine_role)
        # attach sqs publishing rights to the SFN role
        self.queue.grant_send_messages(self.state_machine_role)

        # create the state machine

        # read in the ASL definition
        self.sfn_def = ""
        with open(
            "lambda_orchestration_cdk/statemachine/statemachine.asl.json",
            encoding="utf8",
        ) as fp:
            self.sfn_def = fp.read()

        self.state_machine = _sfn.CfnStateMachine(
            self,
            "SampleStateMachine",
            role_arn=self.state_machine_role.role_arn,
            definition_string=self.sfn_def,
            definition_substitutions={
                "checkPriceFnArn": self.lambdaList["check-price"].function_arn,
                "BuySellFnArn": self.lambdaList["buy-sell-recommend"].function_arn,
                "queueUrl": self.queue.queue_url,
                "buyFnArn": self.lambdaList["buy"].function_arn,
                "sellFnArn": self.lambdaList["sell"].function_arn,
                "topic": self.topic.topic_arn,
            },
        )
        # grant the buy/sell lambda function permission to send task status to the SFN
        self.buySellFunction.add_to_role_policy(
            iam_.PolicyStatement(
                actions=["states:SendTaskSuccess", "states:SendTaskFailure"],
                effect=iam_.Effect.ALLOW,
                resources=[self.state_machine.attr_arn],
            )
        )

        # Outputs
        outputs_(self, "StateMachineName", value=self.state_machine.attr_name)
        outputs_(self, "StateMachineArn", value=self.state_machine.attr_arn)
        outputs_(self, "TopicName", value=self.topic.topic_arn)
