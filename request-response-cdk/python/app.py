#!/usr/bin/env python

from aws_cdk import (
    Stack,
    App,
    aws_sns as sns,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)

from constructs import Construct


class RequestResponseStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create Amazon SNS target topic
        self.topic = sns.Topic(
            self,
            "SNSTopic",
            topic_name=f"{self.stack_name}-topic",
        )

        # Create a Wait state
        wait_timestamp = sfn.Wait(
            self,
            "Wait for timestamp",
            time=sfn.WaitTime.seconds_path("$.timer_seconds"),
        )

        # Create a Task state which publishes a message to a SNS topic
        sendMessageToSns = tasks.SnsPublish(
            self,
            "Send message to SNS",
            topic=self.topic,
            integration_pattern=sfn.IntegrationPattern.REQUEST_RESPONSE,
            # message=sfn.TaskInput.from_object({"input": "Hello from Step Functions!"}),
            message=sfn.TaskInput.from_object(
                {"input": sfn.JsonPath.string_at("$.message")}
            ),
        )

        # Create AWS Step Function state machine
        request_response_state_machine = sfn.StateMachine(
            self,
            "RequestResponse",
            definition=sfn.Chain.start(wait_timestamp.next(sendMessageToSns)),
        )

        # Add permissions for state machine to publish to SNS topic
        self.topic.grant_publish(request_response_state_machine)


app = App()
RequestResponseStack(
    app,
    "RequestResponsePython",
)
app.synth()
