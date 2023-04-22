from aws_cdk import (
    Stack,
    CfnParameter,
    aws_lambda,
    Duration,
    aws_apigateway as apigateway,
    CfnOutput,
    Duration,
    aws_iam,
    aws_sns,
    aws_sns_subscriptions as subscriptions,
    aws_stepfunctions as stepfunctions,
    aws_stepfunctions_tasks as tasks,
    Aws,
    aws_events,
    aws_events_targets as targets,
)

import os
from constructs import Construct

dirname = os.path.dirname(__file__)


class AutomateSecurityIncidentStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        admin_email_address: str,
        restricted_actions: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SNS topic for user alert and email subscription
        alert_topic = aws_sns.Topic(self, "AlertTopic")
        alert_topic.add_subscription(
            subscriptions.EmailSubscription(admin_email_address)
        )

        # Lambda functions related resources
        receive_user_lambda = aws_lambda.Function(
            self,
            "ReceiveUserLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_asset(
                os.path.join(dirname, "functions", "receive-user")
            ),
            handler="receive_user.handler",
            timeout=Duration.seconds(30),
        )

        receive_user_lambda.role.attach_inline_policy(
            aws_iam.Policy(
                self,
                "ReceiveUserPolicy",
                statements=[
                    aws_iam.PolicyStatement(
                        actions=[
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                        ],
                        resources=["arn:aws:logs:*:*:*"],
                    ),
                    aws_iam.PolicyStatement(
                        actions=[
                            "states:SendTaskSuccess",
                        ],
                        resources=["arn:aws:states:*:*"],
                    ),
                ],
            )
        )
        api = apigateway.LambdaRestApi(
            self,
            "secuirty-incident-automation-api",
            handler=receive_user_lambda,
            proxy=False,
        )

        # deployment = apigateway.Deployment(self, "Deployment", api=api)
        # stage = apigateway.Stage(
        #    self,
        #    "dev",
        #    deployment=deployment,
        # )
        # api.deployment_stage = stage

        allow_resource = api.root.add_resource("allow")
        allow_resource.add_method("GET")  # GET /items

        deny_resource = api.root.add_resource("deny")
        deny_resource.add_method("GET")  # GET /items

        validate_policy_lambda = aws_lambda.Function(
            self,
            "ValidatePolicyLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_asset(
                os.path.join(dirname, "functions", "validate-policy")
            ),
            handler="validate_policy.handler",
            timeout=Duration.seconds(300),
            environment={
                "RESTRICTED_ACTIONS": restricted_actions,
            },
        )

        policy_changer_approve_lambda = aws_lambda.Function(
            self,
            "PolicyChangerApproveLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_asset(
                os.path.join(dirname, "functions", "policy-changer-approve")
            ),
            handler="policy_changer_approve.handler",
            timeout=Duration.seconds(300),
            environment={
                "RESTRICTED_ACTIONS": restricted_actions,
            },
        )
        policy_changer_approve_lambda.role.attach_inline_policy(
            aws_iam.Policy(
                self,
                "PolicyChangerApprovePolicy",
                statements=[
                    aws_iam.PolicyStatement(
                        actions=["iam:CreatePolicyVersion"],
                        resources=["*"],
                    )
                ],
            )
        )

        revert_policy_lambda = aws_lambda.Function(
            self,
            "RevertPolicyLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_asset(
                os.path.join(dirname, "functions", "revert-policy")
            ),
            handler="revert_policy.handler",
            timeout=Duration.seconds(300),
            environment={
                "RESTRICTED_ACTIONS": restricted_actions,
            },
        )
        revert_policy_lambda.role.attach_inline_policy(
            aws_iam.Policy(
                self,
                "RevertPolicyPolicy",
                statements=[
                    aws_iam.PolicyStatement(
                        actions=["iam:CreatePolicyVersion", "iam:DeletePolicyVersion"],
                        resources=["*"],
                    )
                ],
            )
        )

        ask_user_lambda = aws_lambda.Function(
            self,
            "AskUserLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_asset(
                os.path.join(dirname, "functions", "ask-user")
            ),
            handler="ask_user.handler",
            timeout=Duration.seconds(300),
            environment={
                "RESTRICTED_ACTIONS": restricted_actions,
                "TOPIC_ARN": alert_topic.topic_arn,
                "API_ALLOW_ENDPOINT": api.url_for_path(path="/allow"),
                "API_DENY_ENDPOINT": api.url_for_path(path="/deny"),
            },
        )
        ask_user_lambda.role.attach_inline_policy(
            aws_iam.Policy(
                self,
                "AskUserPolicy",
                statements=[
                    aws_iam.PolicyStatement(
                        actions=["sns:Publish"],
                        resources=["*"],
                    )
                ],
            )
        )

        # State machine related resources
        modify_state_task = stepfunctions.Pass(
            self,
            "ModifyStateTask",
            parameters={
                "policy.$": "$.detail.requestParameters.policyDocument",
                "accountId.$": "$.detail.userIdentity.accountId",
                "region.$": "$.region",
                "policyMeta.$": "$.detail.responseElements.policy",
            },
            result_path="$",
        )

        validate_policy_task = tasks.LambdaInvoke(
            self,
            "ValidatePolicyChangeTask",
            lambda_function=validate_policy_lambda,
            result_path="$.taskresult",
        )

        revert_policy_task = tasks.LambdaInvoke(
            self,
            "RevertPolicyChangeTask",
            lambda_function=revert_policy_lambda,
            result_path="$.taskresult",
        )

        allow_with_notification_task = tasks.SnsPublish(
            self,
            "NotifyUserTask",
            message=stepfunctions.TaskInput.from_json_path_at(
                "$.taskresult.Payload.message"
            ),
            subject="Policy change detected!",
            topic=alert_topic,
        )

        ask_user_task = tasks.LambdaInvoke(
            self,
            "WaitForUserResponseTask",
            lambda_function=ask_user_lambda,
            payload=stepfunctions.TaskInput.from_object(
                {
                    "token": stepfunctions.JsonPath.task_token,
                }
            ),
            integration_pattern=stepfunctions.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            result_path="$.taskresult",
        )

        approved_task = tasks.LambdaInvoke(
            self,
            "ApprovedTask",
            lambda_function=policy_changer_approve_lambda,
        )

        denied_task = stepfunctions.Pass(self, "DeniedTask")

        validation_result_choice = stepfunctions.Choice(
            self, "AllowOrRevertPolicyChange"
        )
        validation_result_remedy = stepfunctions.Condition.string_equals(
            variable="$.taskresult.Payload.action", value="remedy"
        )
        validation_result_alert = stepfunctions.Condition.string_equals(
            variable="$.taskresult.Payload.action", value="alert"
        )
        user_choice = stepfunctions.Choice(self, "UserAllowsOrDenies")

        user_choice_denied = stepfunctions.Condition.string_equals(
            variable="$.taskresult.action", value="deny"
        )
        user_choice_allow = stepfunctions.Condition.string_equals(
            variable="$.taskresult.action", value="allow"
        )

        step_function_def = (
            stepfunctions.Chain.start(modify_state_task)
            .next(validate_policy_task)
            .next(
                validation_result_choice.when(
                    validation_result_remedy,
                    revert_policy_task.next(ask_user_task).next(
                        user_choice.when(user_choice_denied, denied_task).when(
                            user_choice_allow, approved_task
                        )
                    ),
                ).when(validation_result_alert, allow_with_notification_task)
            )
        )

        states_execution_role = aws_iam.Role(
            self,
            "StatesExecutionRole",
            assumed_by=aws_iam.ServicePrincipal(f"states.{Aws.REGION}.amazonaws.com"),
        )
        states_execution_policy = aws_iam.Policy(
            self,
            "StatesExecutionPolicy",
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["lambda:InvokeFunction"],
                    resources=[
                        validate_policy_lambda.function_arn,
                        ask_user_lambda.function_arn,
                        receive_user_lambda.function_arn,
                        policy_changer_approve_lambda.function_arn,
                        revert_policy_lambda.function_arn,
                    ],
                ),
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["iam:CreatePolicyVersion"],
                    resources=[policy_changer_approve_lambda.function_arn],
                ),
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["iam:DeletePolicyVersion"],
                    resources=[revert_policy_lambda.function_arn],
                ),
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["sns:Publish"],
                    resources=[alert_topic.topic_arn],
                ),
            ],
        )

        statemachine = stepfunctions.StateMachine(
            self,
            "StateMachine",
            definition=step_function_def,
        )
        statemachine.role.attach_inline_policy(states_execution_policy)
        statemachine.role.grant_assume_role(
            aws_iam.ServicePrincipal(f"states.{Aws.REGION}.amazonaws.com")
        )

        cloudwatch_events_execution_role = aws_iam.Role(
            self,
            "CloudwatchEventsExecutionRole",
            assumed_by=aws_iam.ServicePrincipal("events.amazonaws.com"),
        )
        start_step_function_policy = aws_iam.Policy(
            self,
            "StartStepFunctionPolicy",
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["states:StartExecution"],
                    resources=[statemachine.state_machine_arn],
                ),
            ],
        )

        cloudwatch_events_execution_role.attach_inline_policy(
            start_step_function_policy
        )

        new_policy_created_rule = aws_events.Rule(
            self,
            "NewPolicyCreatedRule",
            event_pattern=aws_events.EventPattern(
                source=["aws.iam"],
                detail_type=["AWS API Call via CloudTrail"],
                detail={
                    "eventSource": ["iam.amazonaws.com"],
                    "eventName": ["CreatePolicy"],
                },
            ),
        )

        new_policy_created_rule.add_target(
            targets.SfnStateMachine(statemachine, role=cloudwatch_events_execution_role)
        )
