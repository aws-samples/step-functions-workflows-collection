import logging
import json
import os
from time import sleep
from unittest import TestCase
from uuid import uuid4

import boto3
from botocore.client import BaseClient

"""
Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test.
"""


class TestStateMachine(TestCase):
    """
    This integration test will execute the step function and verify the output
    """

    state_machine_arn: str

    client: BaseClient

    @classmethod
    def get_and_verify_stack_name(cls) -> str:
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        if not stack_name:
            raise Exception(
                "Cannot find env var AWS_SAM_STACK_NAME. \n"
                "Please setup this environment variable with the stack name where we are running integration tests."
            )

        # Verify stack exists
        client = boto3.client("cloudformation")
        try:
            client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name}. \n" f'Please make sure stack with the name "{stack_name}" exists.'
            ) from e

        return stack_name

    @classmethod
    def setUpClass(cls) -> None:
        """
        Based on the provided env variable AWS_SAM_STACK_NAME,
        here we use cloudformation API to find out the ChainedStateMachine's ARN
        """
        stack_name = TestStateMachine.get_and_verify_stack_name()

        client = boto3.client("cloudformation")
        response = client.list_stack_resources(StackName=stack_name)
        resources = response["StackResourceSummaries"]
        state_machine_resources = [
            resource for resource in resources if resource["LogicalResourceId"] == "ChainedStateMachine"
        ]
        if not state_machine_resources:
            raise Exception("Cannot find ChainedStateMachine")

        cls.state_machine_arn = state_machine_resources[0]["PhysicalResourceId"]


    def setUp(self) -> None:
        self.client = boto3.client("stepfunctions")

    def _start_execute(self, input_data) -> str:
        """
        Start the state machine execution request and record the execution ARN
        """
        response = self.client.start_execution(
            stateMachineArn=self.state_machine_arn, name=f"integ-test-{uuid4()}", input=json.dumps(input_data)
        )
        return response["executionArn"]

    def _wait_execution(self, execution_arn: str):
        while True:
            response = self.client.describe_execution(executionArn=execution_arn)
            status = response["status"]
            if status == "SUCCEEDED":
                logging.info(f"Execution {execution_arn} completely successfully.")
                break
            elif status == "RUNNING":
                logging.info(f"Execution {execution_arn} is still running, waiting")
                sleep(3)
            else:
                self.fail(f"Execution {execution_arn} failed with status {status}")

    def _retrieve_execution_output(self, execution_arn: str) -> dict:
        response = self.client.describe_execution(executionArn=execution_arn)
        return json.loads(response["output"])

    def test_state_machine(self):
        input = {
            "dispense": "185"
        }
        execution_arn = self._start_execute(input)
        self._wait_execution(execution_arn)
        output = self._retrieve_execution_output(execution_arn)

        assert output["dispense"] == "0"
        assert output["50s"] == "3"
        assert output["20s"] == "1"
        assert output["10s"] == "1"
        assert output["1s"] == "5"
