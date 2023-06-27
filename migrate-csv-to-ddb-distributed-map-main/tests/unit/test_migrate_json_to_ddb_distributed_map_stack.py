import aws_cdk as core
import aws_cdk.assertions as assertions

from migrate_csv_to_ddb_distributed_map.migrate_csv_to_ddb_distributed_map_stack import MigrateCSVToDdbDistributedMapStack

# example tests. To run these tests, uncomment this file along with the example
# resource in migrate_csv_to_ddb_distributed_map/migrate_csv_to_ddb_distributed_map_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = MigrateCSVToDdbDistributedMapStack(app, "migrate-json-to-ddb-distributed-map")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
