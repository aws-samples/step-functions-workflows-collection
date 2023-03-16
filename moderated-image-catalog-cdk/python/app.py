#!/usr/bin/env python

from aws_cdk import (
    App,
    CfnOutput,
    RemovalPolicy,
    Stack,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_kms as kms,
    aws_s3 as s3,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)

from constructs import Construct


class ModeratedImageCatalogStack(Stack):
    def __init__(
        self, scope: Construct, id: str, moderator_email: str, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Create Amazon S3 bucket to which images as input for the workflow will be uploaded.
        self.ingestion_bucket = s3.Bucket(
            self,
            "IngestionBucket",
            encryption=s3.BucketEncryption.KMS_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,  # note this parameter deletes the bucket upon stack removal
            auto_delete_objects=True,  # note that this parameter deletes bucket content upon stack removal using an AWS Lambda function
        )

        # Create Amazon DynamoDB table to which the workflow will write image metadata if it detects
        # objects or text in processed images.
        self.catalog_table = dynamodb.Table(
            self,
            "CatalogTable",
            partition_key=dynamodb.Attribute(
                name="Id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,  # note this parameter deletes the table and its data upon stack removal
        )

        # Create SNS Topic for moderator notifications
        sns_key = kms.Alias.from_alias_name(self, "SnsKey", "alias/aws/sns")
        self.moderator_notification_topic = sns.Topic(
            self,
            "ModeratorNotificationTopic",
            topic_name="ModeratorNotificationTopic-python",
            master_key=sns_key,
        )
        # Subscribe moderator to notifications
        self.moderator_notification_topic.add_subscription(
            subscriptions.EmailSubscription(moderator_email)
        )

        # AWS Step Function Definition

        # Step to call Amazon Rekognition to check for inappropriate content
        check_for_inappropriate_content = tasks.CallAwsService(
            self,
            "Check for inappropriate content",
            service="rekognition",
            action="detectModerationLabels",
            parameters={
                "Image": {
                    "S3Object": {
                        "Bucket": sfn.JsonPath.string_at("$.bucket"),
                        "Name": sfn.JsonPath.string_at("$.key"),
                    }
                }
            },
            result_path="$.moderationResult",
            iam_resources=["*"],
            additional_iam_statements=[
                iam.PolicyStatement(
                    actions=["s3:getObject"],
                    resources=[f"{self.ingestion_bucket.bucket_arn}/*"],
                )
            ],
        )

        # Choice step depending on whether inappropriate content has been detected
        has_inappropriate_content_been_detected = sfn.Choice(
            self, "Inappropriate content detected?"
        )
        inappropriate_content_detected = sfn.Condition.is_present(
            "$.moderationResult.ModerationLabels[0]"
        )

        # Step to notify content moderators via SNS Topic
        notify_content_moderators = tasks.SnsPublish(
            self,
            "Notify content moderators",
            topic=self.moderator_notification_topic,
            integration_pattern=sfn.IntegrationPattern.REQUEST_RESPONSE,
            message=sfn.TaskInput.from_json_path_at("$"),
        )

        # Step to call Amazon Rekognition to detect objects
        detect_objects_in_image = tasks.CallAwsService(
            self,
            "Detect objects in image",
            service="rekognition",
            action="detectLabels",
            parameters={
                "Image": {
                    "S3Object": {
                        "Bucket": sfn.JsonPath.string_at("$.bucket"),
                        "Name": sfn.JsonPath.string_at("$.key"),
                    }
                }
            },
            result_path="$.output",
            iam_resources=["*"],
            additional_iam_statements=[
                iam.PolicyStatement(
                    actions=["s3:getObject"],
                    resources=[f"{self.ingestion_bucket.bucket_arn}/*"],
                )
            ],
        )

        # Step to call Amazon Rekognition to detect text
        detect_text_in_image = tasks.CallAwsService(
            self,
            "Detect text in image",
            service="rekognition",
            action="detectText",
            parameters={
                "Image": {
                    "S3Object": {
                        "Bucket": sfn.JsonPath.string_at("$.bucket"),
                        "Name": sfn.JsonPath.string_at("$.key"),
                    }
                }
            },
            result_path="$.output",
            iam_resources=["*"],
            additional_iam_statements=[
                iam.PolicyStatement(
                    actions=["s3:getObject"],
                    resources=[f"{self.ingestion_bucket.bucket_arn}/*"],
                )
            ],
        )

        # Step to record object metadata found in image in DynamoDB table
        record_objects_in_database = tasks.DynamoUpdateItem(
            self,
            "Record objects in database",
            table=self.catalog_table,
            key={
                "Id": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.key")
                )
            },
            update_expression="SET detectedObjects = :o",
            expression_attribute_values={
                ":o": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.json_to_string(
                        sfn.JsonPath.object_at("$.output.Labels")
                    )
                )
            },
        )

        # Step to record text metadata found in image in DynamoDB table
        record_text_in_database = tasks.DynamoUpdateItem(
            self,
            "Record text in database",
            table=self.catalog_table,
            key={
                "Id": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.key")
                )
            },
            update_expression="SET detectedText = :t",
            expression_attribute_values={
                ":t": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.json_to_string(
                        sfn.JsonPath.object_at("$.output.TextDetections")
                    )
                )
            },
        )

        # Parallel step which processes the image in parallel branches
        process_image = sfn.Parallel(self, "Process image")
        # Branch #1
        process_image.branch(detect_objects_in_image.next(record_objects_in_database))
        # Branch #2
        process_image.branch(detect_text_in_image.next(record_text_in_database))

        sfn.StateMachine(
            self,
            "ModeratedImageCatalog",
            state_machine_name="moderated-image-catalog-workflow-python",
            definition=sfn.Chain.start(
                check_for_inappropriate_content.next(
                    has_inappropriate_content_been_detected.when(
                        inappropriate_content_detected, notify_content_moderators
                    ).otherwise(process_image)
                )
            ),
        )

        # Outputs to assist with testing
        CfnOutput(
            self,
            "IngestionBucketOutput",
            description="S3 bucket name",
            value=self.ingestion_bucket.bucket_name,
        )
        CfnOutput(
            self,
            "CatalogTableOutput",
            description="DynamoDB table name",
            value=self.catalog_table.table_name,
        )
        CfnOutput(
            self,
            "ModeratorSNSTopicOutput",
            description="SNS topic ARN",
            value=self.moderator_notification_topic.topic_arn,
        )


app = App()
ModeratedImageCatalogStack(
    app, "ModeratedImageCatalogPython", moderator_email="moderator@example.com"
)
app.synth()
