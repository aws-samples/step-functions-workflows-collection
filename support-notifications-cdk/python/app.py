#!/usr/bin/env python

from aws_cdk import (
    App,
    Environment,
    Stack,
    aws_events as events,
    aws_events_targets as targets,
    aws_kms as kms,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
import os
from constructs import Construct


class support_notifications(Stack):
    def __init__(
        self, scope: Construct, id: str, notification_email: str, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Create SNS Topic for notifications of new case creation which match the severity level
        sns_key = kms.Alias.from_alias_name(self, "SnsKey", "alias/aws/sns")
        support_notifications_topic = sns.Topic(
            self,
            "SupportCasesCreatedNotification",
            master_key=sns_key,
        )
        # Subscribe to notifications
        support_notifications_topic.add_subscription(
            subscriptions.EmailSubscription(notification_email)
        )

        # AWS Step Function Definition

        # Step to call AWS Support API to retrieve information about the newly created case
        get_support_case = tasks.CallAwsService(
            self,
            "Get Support Case Details",
            service="support",
            action="describeCases",
            parameters={"CaseIdList": sfn.JsonPath.array(sfn.JsonPath.entire_payload)},
            input_path="$.detail.case-id",
            result_path="$.CaseDetails",
            iam_resources=["*"],
        )

        # Choice step depending on whether the case matches either the urgent or critical severity level we want to notify on.
        # This is refers to "Production system down" or "Business-critical system down" in AWS console.
        # https://docs.aws.amazon.com/awssupport/latest/APIReference/API_SeverityLevel.html#API_SeverityLevel_Contents
        determine_severity = sfn.Choice(self, "Determine Severity")
        match_severity = sfn.Condition.or_(
            sfn.Condition.string_equals(
                "$.CaseDetails.Cases[0].SeverityCode", "critical"
            ),
            sfn.Condition.string_equals(
                "$.CaseDetails.Cases[0].SeverityCode", "urgent"
            ),
        )

        # Step to notify of a new case being created via SNS Topic.
        notify_new_case_created = tasks.SnsPublish(
            self,
            "Notify that a new case has been created",
            topic=support_notifications_topic,
            integration_pattern=sfn.IntegrationPattern.REQUEST_RESPONSE,
            subject=sfn.JsonPath.format(
                "AWS Support Case Created - Case ID: {} - {}",
                sfn.JsonPath.string_at("$.CaseDetails.Cases[0].DisplayId"),
                sfn.JsonPath.string_at("$.CaseDetails.Cases[0].Subject"),
            ),
            message=sfn.TaskInput.from_text(
                sfn.JsonPath.format(
                    "A new AWS Support case (Case ID: {}) has been opened in account {}, with a {} severity by {}. The subject is {}. You can access this case by logging into AWS account {} and clicking the following link: https://console.aws.amazon.com/support/home#/case/?displayId={}&language=en",
                    sfn.JsonPath.string_at("$.CaseDetails.Cases[0].DisplayId"),
                    sfn.JsonPath.string_at("$.account"),
                    sfn.JsonPath.string_at("$.CaseDetails.Cases[0].SeverityCode"),
                    sfn.JsonPath.string_at("$.CaseDetails.Cases[0].SubmittedBy"),
                    sfn.JsonPath.string_at("$.CaseDetails.Cases[0].Subject"),
                    sfn.JsonPath.string_at("$.account"),
                    sfn.JsonPath.string_at("$.CaseDetails.Cases[0].DisplayId"),
                )
            ),
        )

        finished = sfn.Succeed(self, "Notification not required")

        support_notifications_state_machine = sfn.StateMachine(
            self,
            "SupportNotificationsStateMachine",
            state_machine_name="support-notifications-python",
            definition=sfn.Chain.start(
                get_support_case.next(
                    determine_severity.when(
                        match_severity, notify_new_case_created
                    ).otherwise(finished)
                )
            ),
        )
        # EventBridge rule that triggers the state machine whenever a support case is created.
        events.Rule(
            self,
            "SupportCaseCreatedTrigger",
            event_pattern=events.EventPattern(
                source=["aws.support"],
                detail={"event-name": ["CreateCase"]},
            ),
            targets=[targets.SfnStateMachine(support_notifications_state_machine)],
        )


app = App()
# Note that the AWS Support API is only available from the us-east-1 region.
support_env = Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region="us-east-1")

support_notifications(
    app,
    "SupportNotificationsPython",
    notification_email="admin@example.com",
    env=support_env,
)
app.synth()
