from aws_cdk import (
    Stack,
    CfnParameter,
    CfnOutput,
    Duration,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_apigateway as apigw,
    aws_stepfunctions as sfn,
)
from constructs import Construct


class HumanInTheLoopCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        moderator_email = CfnParameter(
            self, "ModeratorEmailAddress",
            type="String",
            default="moderator@example.com",
            description="Enter the email address that will receive review notifications."
        )

        notification_topic = sns.Topic(self, "NotificationTopic")
        notification_topic.add_subscription(
            subscriptions.EmailSubscription(moderator_email.value_as_string)
        )

        approval_api = apigw.RestApi(self, "HumanApprovalApi",
            rest_api_name="HumanApprovalApi"
        )
        respond_resource = approval_api.root.add_resource("respond")

        api_endpoint = f"https://{approval_api.rest_api_id}.execute-api.{self.region}.amazonaws.com/prod/respond"

        send_approval_email_fn = _lambda.Function(self, "SendApprovalEmailFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="send_approval_email.lambda_handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "SNS_TOPIC_ARN": notification_topic.topic_arn,
                "API_ENDPOINT": api_endpoint,
            }
        )
        notification_topic.grant_publish(send_approval_email_fn)

        handle_approval_fn = _lambda.Function(self, "HandleApprovalFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="handle_approval.lambda_handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=512,
        )
        handle_approval_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["states:SendTaskSuccess", "states:SendTaskFailure"],
                resources=["*"],
            )
        )

        respond_resource.add_method("GET",
            apigw.LambdaIntegration(handle_approval_fn)
        )

        processing_fn = _lambda.Function(self, "ProcessingLambda",
            runtime=_lambda.Runtime.NODEJS_24_X,
            handler="app.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=512,
        )

        sfn_def = ""
        with open("statemachine/statemachine.asl.json", encoding="utf8") as fp:
            sfn_def = fp.read()

        state_machine_role = iam.Role(self, "StateMachineRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )
        state_machine_role.attach_inline_policy(
            iam.Policy(self, "StateMachineLambdaPolicy",
                statements=[
                    iam.PolicyStatement(
                        actions=["lambda:InvokeFunction"],
                        resources=[
                            send_approval_email_fn.function_arn,
                            processing_fn.function_arn,
                        ],
                    )
                ],
            )
        )

        state_machine = sfn.CfnStateMachine(self, "HumanInTheLoopStateMachine",
            role_arn=state_machine_role.role_arn,
            definition_string=sfn_def,
            definition_substitutions={
                "SendApprovalEmailFunction": send_approval_email_fn.function_arn,
                "ProcessingLambda": processing_fn.function_name,
            },
            state_machine_name="human-in-the-loop-cdk",
        )

        CfnOutput(self, "StepFunctionConsoleUrl",
            value=f"https://{self.region}.console.aws.amazon.com/states/home?region={self.region}#/statemachines/view/{state_machine.attr_arn}"
        )
        CfnOutput(self, "ApiEndpoint",
            value=api_endpoint
        )
