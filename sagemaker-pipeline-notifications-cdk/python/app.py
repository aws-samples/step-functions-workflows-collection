#!/usr/bin/env python

from aws_cdk import (
    App,
    Stack,
    aws_events as events,
    aws_events_targets as targets,
    aws_kms as kms,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


class sagemaker_pipeline_notifications(Stack):
    def __init__(
        self, scope: Construct, id: str, notification_email: str, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Create SNS Topic for notifications of failed SageMaker Pipeline executions
        sns_key = kms.Alias.from_alias_name(self, "SnsKey", "alias/aws/sns")
        sagemaker_pipeline_notifications_topic = sns.Topic(
            self,
            "SageMakerPipelineFailedNotification",
            master_key=sns_key,
        )
        # Subscribe to notifications
        sagemaker_pipeline_notifications_topic.add_subscription(
            subscriptions.EmailSubscription(notification_email)
        )

        # AWS Step Function Definition

        # Step to notify of a failed SageMaker Pipeline execution via SNS Topic.
        notify_failed_sagemaker_pipeline_execution = tasks.SnsPublish(
            self,
            "Notify that a SageMaker Pipeline execution has failed",
            topic=sagemaker_pipeline_notifications_topic,
            integration_pattern=sfn.IntegrationPattern.REQUEST_RESPONSE,
            subject=sfn.JsonPath.format(
                "Amazon SageMaker Pipeline Failed - Pipeline Name: {}",
                sfn.JsonPath.array_get_item(
                    sfn.JsonPath.string_split(
                        sfn.JsonPath.string_at("$.detail.pipelineArn"), "/"
                    ),
                    1,
                ),
            ),
            message=sfn.TaskInput.from_text(
                sfn.JsonPath.format(
                    "The SageMaker Pipeline, {}, started at {} and failed at {}.",
                    sfn.JsonPath.array_get_item(
                        sfn.JsonPath.string_split(
                            sfn.JsonPath.string_at("$.detail.pipelineArn"), "/"
                        ),
                        1,
                    ),
                    sfn.JsonPath.string_at("$.detail.executionStartTime"),
                    sfn.JsonPath.string_at("$.detail.executionEndTime"),
                )
            ),
        )

        sagemaker_pipeline_notifications_state_machine = sfn.StateMachine(
            self,
            "SageMakerPipelineNotificationsStateMachine",
            state_machine_name="sagemaker-pipeline-notifications-python",
            definition=sfn.Chain.start(notify_failed_sagemaker_pipeline_execution),
        )

        # EventBridge rule that triggers the state machine whenever a SageMaker Pipeline execution fails.
        events.Rule(
            self,
            "SageMakerPipelineExecutionFailedTrigger",
            event_pattern=events.EventPattern(
                source=["aws.sagemaker"],
                detail={"currentPipelineExecutionStatus": ["Failed"]},
                detail_type=[
                    "SageMaker Model Building Pipeline Execution Status Change"
                ],
            ),
            targets=[
                targets.SfnStateMachine(sagemaker_pipeline_notifications_state_machine)
            ],
        )


app = App()

sagemaker_pipeline_notifications(
    app,
    "SageMakerPipelineNotificationsPython",
    notification_email="admin@example.com",
)
app.synth()
