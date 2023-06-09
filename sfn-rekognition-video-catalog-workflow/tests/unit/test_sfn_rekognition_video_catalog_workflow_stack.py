import aws_cdk as core
import aws_cdk.assertions as assertions

from sfn_rekognition_video_catalog_workflow.sfn_rekognition_video_catalog_workflow_stack import SfnRekognitionVideoCatalogWorkflowStack

# example tests. To run these tests, uncomment this file along with the example
# resource in sfn_rekognition_video_catalog_workflow/sfn_rekognition_video_catalog_workflow_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = SfnRekognitionVideoCatalogWorkflowStack(app, "sfn-rekognition-video-catalog-workflow")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
