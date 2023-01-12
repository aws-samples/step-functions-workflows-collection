import aws_cdk as core
import aws_cdk.assertions as assertions

from ingest_and_analyze_historical_storm_events.ingest_and_analyze_historical_storm_events_stack import IngestAndAnalyzeHistoricalStormEventsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in ingest_and_analyze_historical_storm_events/ingest_and_analyze_historical_storm_events_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = IngestAndAnalyzeHistoricalStormEventsStack(app, "ingest-and-analyze-historical-storm-events")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
