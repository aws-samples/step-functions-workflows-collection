import aws_cdk as core
import aws_cdk.assertions as assertions

from lambda_orchestration_cdk.lambda_orchestration_cdk_stack import LambdaOrchestrationCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in lambda_orchestration_cdk/lambda_orchestration_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = LambdaOrchestrationCdkStack(app, "lambda-orchestration-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
