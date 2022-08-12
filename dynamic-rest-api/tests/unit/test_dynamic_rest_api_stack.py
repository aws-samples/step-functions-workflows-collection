import aws_cdk as core
import aws_cdk.assertions as assertions

from dynamic_rest_api.dynamic_rest_api_stack import DynamicRestApiStack

# example tests. To run these tests, uncomment this file along with the example
# resource in dynamic_rest_api/dynamic_rest_api_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = DynamicRestApiStack(app, "dynamic-rest-api")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
