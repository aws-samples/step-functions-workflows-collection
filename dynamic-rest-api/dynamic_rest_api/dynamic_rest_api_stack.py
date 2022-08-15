from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
)
from constructs import Construct
from . import dynamic_rest_api

class DynamicRestApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "DynamicRestApiQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )

        dynamic_rest_api.DynamicRestApi(self, "DynamicRestApi")