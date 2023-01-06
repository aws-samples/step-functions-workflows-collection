import aws_cdk as core
import aws_cdk.assertions as assertions

from eventbridge_custom_cdk.eventbridge_custom_cdk_stack import EventbridgeCustomCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in eventbridge_custom_cdk/eventbridge_custom_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = EventbridgeCustomCdkStack(app, "eventbridge-custom-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
