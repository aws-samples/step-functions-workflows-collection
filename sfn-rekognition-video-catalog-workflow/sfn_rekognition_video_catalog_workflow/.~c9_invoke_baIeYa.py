import os
from aws_cdk import (
    Duration,
    App,
    CfnOutput,
    RemovalPolicy,
    Stack,
    # aws_sqs as sqs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_s3 as s3,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_dynamodb as dynamo_db,
    aws_logs as logs,
    aws_glue as glue,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions
)
from constructs import Construct

VIDEO_CONTENT_DATA_CRAWLER_NAME = "video_content_data_crawler"

class SfnRekognitionVideoCatalogWorkflowStack(Stack):

    def __init__(
        self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account = os.environ["CDK_DEFAULT_ACCOUNT"]
        region = os.environ["CDK_DEFAULT_REGION"]
        # The code that defines your stack goes here
        sfn_log_group_name = "ProcessVideoContentStateMachine-" + account + '-' + region + '-Logs'
        # Define cloudwatch log group for Step Function logs
        step_function_log_group = logs.LogGroup(self, "StepFunctionLogGroup", log_group_name=sfn_log_group_name, removal_policy=RemovalPolicy.DESTROY)
        
        # create amazon sns target topic
        self.topic = sns.Topic(self,"rekognitionNotifications-topic")
        
        # create role policy for rekognition to publish to topic
        rekognition_service_role = iam.Role(self, id="rekognition-service-sns-publish-policy",
            assumed_by=iam.ServicePrincipal('rekognition.amazonaws.com'),
            role_name='rekognition-service-sns-role',
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess')]
            )
        rekognition_service_role.add_to_policy(iam.PolicyStatement(
          resources=[self.topic.topic_arn],
          actions=["sns:Publish"]
          ))
        
        # create the buckets
        source_bucket = "videos-for-processing-" + account + '-' + region
        #self.source_bucket = source_bucket
        s3.Bucket(self, source_bucket, bucket_name=source_bucket, removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        
        video_processed_bucket = "videos-processed-" + account + '-' + region
        s3.Bucket(self, video_processed_bucket, bucket_name=video_processed_bucket, removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        #self.video_processed_bucket = video_processed_bucket
        
        video_metadata_lake_bucket = 'video-metadata-lake-' + account + '-' + region
        s3.Bucket(self, video_metadata_lake_bucket, bucket_name=video_metadata_lake_bucket, removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        #self.video_metadata_lake_bucket = video_metadata_lake_bucket
        
        # create dynamodb table
        dynamo_db_table_name ="rekognition-job-tracker"
        dynamo_db.Table(
            self, dynamo_db_table_name, table_name=dynamo_db_table_name, removal_policy=RemovalPolicy.DESTROY,
            partition_key=dynamo_db.Attribute(
                name="video-name",
                type=dynamo_db.AttributeType.STRING
                )
            )
            
        pandaLayer = lambda_.LayerVersion(self, 'lambda-layer',
            code=lambda_.AssetCode('functions/layers/pandas/'),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9]
        )
        
        # create role for lambdas
        wrkflow_lambda_role = iam.Role(self, id='rekognition-wrkflw-lambda-role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            role_name='rekognition-wrkflw-lambda-role',
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')]
        )
        
        wrkflow_lambda_role.add_to_policy(iam.PolicyStatement(
            resources=["arn:aws:s3:::video-metadata-lake/*",
            "arn:aws:s3:::videos-for-detection/*"
            ],
            actions=["s3:PutObject",
            "s3:PutObjectTagging",
            "s3:GetObject",
            "s3:GetObjectTagging"]
            )
        )
        
        post_wrkflw_lambda_role = iam.Role(self, id='post-_rekognition-wrkflw-lambda-role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            role_name='rekognition-post-wrkflw-lambda-role',
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')]
        )
        
        post_wrkflw_lambda_role.add_to_policy(iam.PolicyStatement(
            resources=["arn:aws:s3:::videos-for-detection/*",
            "arn:aws:s3:::videos-processed-archive/*"
            ],
            actions=[
                "s3:PutObject",
            "s3:GetObject",
            "s3:GetObjectTagging",
            "s3:DeleteObject"
            ]
            )
        )
            
        # lambda functions
        callback_lambda = lambda_.Function(self, "stateMachineCallback",
            code=lambda_.Code.from_asset("./functions/stateMachineCallback"),
            handler="index.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            role=wrkflow_lambda_role,
            timeout=Duration.minutes(5)
        )
        
        self.topic.add_subscription(subscriptions.LambdaSubscription(callback_lambda))
        
        write_segment_data_lambda = lambda_.Function(self, "write-segment-data",
            code=lambda_.Code.from_asset("./functions/writeSegmentData"),
            handler="index.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            layers = [pandaLayer],
            environment={
                "video_metadata_lake_bucket":video_metadata_lake_bucket,
                "video_src_bucket":source_bucket
            },
            role=wrkflow_lambda_role,
            timeout=Duration.minutes(5)
        )
        
        write_label_data_lambda =lambda_.Function(self, "write-label-data",
            code=lambda_.Code.from_asset("./functions/writeLabelData"),
            handler="index.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            layers=[pandaLayer],
            environment={
                "video_metadata_lake_bucket":video_metadata_lake_bucket,
                "video_src_bucket":source_bucket
            },
            role=wrkflow_lambda_role,
            timeout=Duration.minutes(5)
        )
        
        write_content_moderated_lambda=lambda_.Function(self, "write-content-moderated-data",
            code=lambda_.Code.from_asset("./functions/writeContentModeratedData"),
            handler="index.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            layers=[pandaLayer],
            environment={
                "video_metadata_lake_bucket":video_metadata_lake_bucket,
                "video_src_bucket":source_bucket
            },
            role=wrkflow_lambda_role,
            timeout=Duration.minutes(5)
        )
        
        move_processed_lambda=lambda_.Function(self, "move-processed-files",
            code=lambda_.Code.from_asset("./functions/moveProcessedFiles"),
            handler="index.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            environment={
                "video_processed_bucket":video_processed_bucket,
                "video_src_bucket":source_bucket
            },
            role=post_wrkflw_lambda_role,
            timeout=Duration.minutes(5)
        )
        
        # create glue db and crawler
        video_content_catalog_db = \
        glue.CfnDatabase(self, "VideoContentCatalogDb",
                      catalog_id=os.environ["CDK_DEFAULT_ACCOUNT"],
                      database_input=glue.CfnDatabase.DatabaseInputProperty(
                        create_table_default_permissions=[
                          glue.CfnDatabase.PrincipalPrivilegesProperty(
                            permissions=["ALL"],
                            principal=glue.CfnDatabase.DataLakePrincipalProperty(
                              data_lake_principal_identifier="IAM_ALLOWED_PRINCIPALS"
                              )
                              )],
                              description="Database of video detected content records",
                              name="video_content_catalog_db"
                        )
                      )
        glue_crawler_role = iam.Role(self,"GlueCrawlerRole",
                            assumed_by=iam.ServicePrincipal("glue.amazonaws.com")
                            )
        glue_crawler_role.add_to_policy(iam.PolicyStatement(
            resources=[f"arn:aws:s3:::{video_metadata_lake_bucket}/*"],
            actions=["s3:GetObject",
                     "s3:PutObject"]
          ))
        glue_crawler_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"))
            
        glue_classifier = glue.CfnClassifier(self, "CsvClassifier",
          csv_classifier=glue.CfnClassifier.CsvClassifierProperty(
            allow_single_column=False,
            contains_header="PRESENT",
            delimiter=",",
            disable_value_trimming=False,
            name="csv_classify",
            quote_symbol="\""
          )
        )
        
        glue.CfnCrawler(self, "VideoContentDataGlueCrawler",
            database_name=video_content_catalog_db.database_input.name,
            name=VIDEO_CONTENT_DATA_CRAWLER_NAME,
            role=glue_crawler_role.role_arn,
            recrawl_policy=glue.CfnCrawler.RecrawlPolicyProperty(
              recrawl_behavior="CRAWL_NEW_FOLDERS_ONLY"
            ),
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                delete_behavior="LOG",
                update_behavior="LOG"
            ),
            targets=glue.CfnCrawler.TargetsProperty(
              s3_targets=[
                glue.CfnCrawler.S3TargetProperty(
                  path=f"s3://{video_metadata_lake_bucket}/",
                  )
                ])
          )
            
        # IAM role for state machine
        stepfunctions_service_principal = "states." + region + ".amazonaws.com"
        
        role = iam.Role(self, "stepfunction-rekognition-workflow-role",
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('AmazonRekognitionReadOnlyAccess'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'),
                iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsDeliveryFullAccessPolicy')],
            assumed_by=iam.ServicePrincipal(stepfunctions_service_principal),
        )
        role.add_to_policy(iam.PolicyStatement(
          resources=[rekognition_service_role.role_arn],
          actions=["iam:GetRole","iam:PassRole"]
          )
        )
        role.add_to_policy(iam.PolicyStatement(
          actions=["glue:StartCrawler"]))
          actions=["glue:StartCrawler"]
          )
        )
        # create state machine
        #statemachine_definition = self.read_statemachine_definition()
        #print(statemachine_definition)
        asl = self.build_video_processing_workflow_definition(
            write_content_moderated_lambda.function_arn,
            write_label_data_lambda.function_arn,
            write_segment_data_lambda.function_arn,
            move_processed_lambda.function_arn,
            source_bucket,
            VIDEO_CONTENT_DATA_CRAWLER_NAME,
            self.topic.topic_arn,
            rekognition_service_role.role_arn
        )
        
        
        sfn.CfnStateMachine(
            self, "ProcessVideoContentStateMachine",
            definition=asl,
            role_arn=role.role_arn,
            logging_configuration = sfn.CfnStateMachine.LoggingConfigurationProperty(
                destinations=[sfn.CfnStateMachine.LogDestinationProperty(
                cloud_watch_logs_log_group=sfn.CfnStateMachine.CloudWatchLogsLogGroupProperty(
                  log_group_arn=step_function_log_group.log_group_arn))],
                  level="ALL"
                  )
        )
        
        
    def read_statemachine_definition(self):
        input_file_name = "statemachine/statemachine.asl.json"
        read_file = open(input_file_name,"rt")
        file_contents = read_file.read()
        read_file.close()
        return file_contents
        
    def build_video_processing_workflow_definition(
        self, 
        content_moderated_lambda_arn,
        label_detection_lambda_arn,
        segment_detection_lambda_arn,
        processed_file_lambda_arn, 
        video_src_bucket_name,
        glue_crawler_name,
        rekognition_sns_topic_arn,
        rekognition_service_role_arn):
                
        asl = {
            "Comment": "A description of my state machine",
            "StartAt": "Content Moderation Map",
            "States": {
                "Content Moderation Map": {
                  "Type": "Map",
                  "ItemProcessor": {
                    "ProcessorConfig": {
                      "Mode": "DISTRIBUTED",
                      "ExecutionType": "STANDARD"
                    },
                    "StartAt": "StartContentModeration",
                    "States": {
                      "StartContentModeration": {
                        "Type": "Task",
                        "Parameters": {
                          "MinConfidence": 95,
                          "Video": {
                            "S3Object": {
                              "Bucket": video_src_bucket_name,
                              "Name.$": "$.Key"
                            }
                          },
                          "NotificationChannel": {
                            "RoleArn": rekognition_service_role_arn,
                            "SnsTopicArn": rekognition_sns_topic_arn
                          }
                        },
                        "Resource": "arn:aws:states:::aws-sdk:rekognition:startContentModeration",
                        "Next": "Wait for ContentModeration Callback",
                        "ResultPath": "$.Rekognition"
                      },
                      "Wait for ContentModeration Callback": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::aws-sdk:dynamodb:putItem.waitForTaskToken",
                        "Parameters": {
                          "TableName": "rekognitionJobTracker",
                          "Item": {
                            "Key": {
                              "S.$": "$.Key"
                            },
                            "video": {
                              "S.$": "$.Key"
                            },
                            "jobid": {
                              "S.$": "$.Rekognition.JobId"
                            },
                            "jobName": {
                              "S": "Content Moderation"
                            },
                            "processingStatus": {
                              "S": "processing"
                            },
                            "taskToken": {
                              "S.$": "$$.Task.Token"
                            }
                          }
                        },
                        "ResultPath": "$.DynamoDBResult",
                        "Next": "GetContentModeration"
                      },
                      "GetContentModeration": {
                        "Type": "Task",
                        "Parameters": {
                          "JobId.$": "$.Rekognition.JobId",
                          "MaxResults": 1000
                        },
                        "Resource": "arn:aws:states:::aws-sdk:rekognition:getContentModeration",
                        "Next": "Update ContentModeration Job status",
                        "ResultPath": "$.Results"
                      },
                      "Update ContentModeration Job status": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::dynamodb:updateItem",
                        "Parameters": {
                          "TableName": "rekognitionJobTracker",
                          "Key": {
                            "video": {
                              "S.$": "$.Key"
                            },
                            "jobid": {
                              "S.$": "$.Rekognition.JobId"
                            }
                          },
                          "UpdateExpression": "SET processingStatus = :processingStatus",
                          "ExpressionAttributeValues": {
                            ":processingStatus": {
                              "S.$": "$.Results.JobStatus"
                            }
                          }
                        },
                        "Next": "Choice",
                        "ResultPath": "$.DynamoDBResult"
                      },
                      "Choice": {
                        "Type": "Choice",
                        "Choices": [
                          {
                            "Variable": "$.Results.ModerationLabels[0]",
                            "IsPresent": True,
                            "Next": "Write Rekognition Content Moderation Results to file"
                          }
                        ],
                        "Default": "Pass"
                      },
                      "Write Rekognition Content Moderation Results to file": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::lambda:invoke",
                        "OutputPath": "$.Payload",
                        "Parameters": {
                          "FunctionName": content_moderated_lambda_arn,
                          "Payload": {
                            "prefix": "content",
                            "Key.$": "$.Key",
                            "Results.$": "$.Results"
                          }
                        },
                        "Retry": [
                          {
                            "ErrorEquals": [
                              "Lambda.ServiceException",
                              "Lambda.AWSLambdaException",
                              "Lambda.SdkClientException",
                              "Lambda.TooManyRequestsException"
                            ],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 6,
                            "BackoffRate": 2
                          }
                        ],
                        "Next": "Pass"
                      },
                      "Pass": {
                        "Type": "Pass",
                        "End": True
                      }
                    }
                  },
                  "Label": "ContentModerationMap",
                  "MaxConcurrency": 10,
                  "ItemReader": {
                    "Resource": "arn:aws:states:::s3:listObjectsV2",
                    "Parameters": {
                      "Bucket": video_src_bucket_name
                    }
                  },
                  "Next": "Segment Detection Map"
                },
                "Segment Detection Map": {
                  "Type": "Map",
                  "ItemProcessor": {
                    "ProcessorConfig": {
                      "Mode": "DISTRIBUTED",
                      "ExecutionType": "STANDARD"
                    },
                    "StartAt": "StartSegmentDetection",
                    "States": {
                      "StartSegmentDetection": {
                        "Type": "Task",
                        "Parameters": {
                          "Filters": {
                            "ShotFilter": {
                              "MinSegmentConfidence": 95
                            },
                            "TechnicalCueFilter": {
                              "BlackFrame": {
                                "MaxPixelThreshold": 0.2,
                                "MinCoveragePercentage": 99
                              },
                              "MinSegmentConfidence": 95
                            }
                          },
                          "NotificationChannel": {
                            "RoleArn": rekognition_service_role_arn,
                            "SnsTopicArn": rekognition_sns_topic_arn
                          },
                          "SegmentTypes": [
                            "SHOT",
                            "TECHNICAL_CUE"
                          ],
                          "Video": {
                            "S3Object": {
                              "Bucket": "videos-for-processing",
                              "Name.$": "$.Key"
                            }
                          }
                        },
                        "Resource": "arn:aws:states:::aws-sdk:rekognition:startSegmentDetection",
                        "ResultPath": "$.Rekognition",
                        "Next": "Wait for SegmentDetection Callback"
                      },
                      "Wait for SegmentDetection Callback": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::aws-sdk:dynamodb:putItem.waitForTaskToken",
                        "Parameters": {
                          "TableName": "rekognitionJobTracker",
                          "Item": {
                            "Key": {
                              "S.$": "$.Key"
                            },
                            "video": {
                              "S.$": "$.Key"
                            },
                            "jobid": {
                              "S.$": "$.Rekognition.JobId"
                            },
                            "jobName": {
                              "S": "Segment Detection"
                            },
                            "processingStatus": {
                              "S": "processing"
                            },
                            "taskToken": {
                              "S.$": "$$.Task.Token"
                            }
                          }
                        },
                        "ResultPath": "$.DynamoDBResult",
                        "Next": "GetSegmentDetection"
                      },
                      "GetSegmentDetection": {
                        "Type": "Task",
                        "Parameters": {
                          "JobId.$": "$.Rekognition.JobId",
                          "MaxResults": 1000
                        },
                        "Resource": "arn:aws:states:::aws-sdk:rekognition:getSegmentDetection",
                        "Next": "Update Segment Detection Status",
                        "ResultPath": "$.Results"
                      },
                      "Update Segment Detection Status": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::dynamodb:updateItem",
                        "Parameters": {
                          "TableName": "rekognitionJobTracker",
                          "Key": {
                            "video": {
                              "S.$": "$.Key"
                            },
                            "jobid": {
                              "S.$": "$.Rekognition.JobId"
                            }
                          },
                          "UpdateExpression": "SET processingStatus = :processingStatus",
                          "ExpressionAttributeValues": {
                            ":processingStatus": {
                              "S.$": "$.Results.JobStatus"
                            }
                          }
                        },
                        "Next": "Write Rekognition Segmet Results to File",
                        "ResultPath": "$.DynamoDBResult"
                      },
                      "Write Rekognition Segmet Results to File": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::lambda:invoke",
                        "OutputPath": "$.Payload",
                        "Parameters": {
                          "FunctionName": segment_detection_lambda_arn,
                          "Payload": {
                            "executionId.$": "$$.Execution.Name",
                            "prefix": "segments",
                            "Key.$": "$.Key",
                            "Results.$": "$.Results"
                          }
                        },
                        "Retry": [
                          {
                            "ErrorEquals": [
                              "Lambda.ServiceException",
                              "Lambda.AWSLambdaException",
                              "Lambda.SdkClientException",
                              "Lambda.TooManyRequestsException"
                            ],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 6,
                            "BackoffRate": 2
                          }
                        ],
                        "End": True
                      }
                    }
                  },
                  "Next": "Label Detection Map",
                  "Label": "SegmentDetectionMap",
                  "MaxConcurrency": 10,
                  "ItemReader": {
                    "Resource": "arn:aws:states:::s3:listObjectsV2",
                    "Parameters": {
                      "Bucket": video_src_bucket_name
                    }
                  }
                },
                "Label Detection Map": {
                  "Type": "Map",
                  "ItemProcessor": {
                    "ProcessorConfig": {
                      "Mode": "DISTRIBUTED",
                      "ExecutionType": "STANDARD"
                    },
                    "StartAt": "StartLabelDetection",
                    "States": {
                      "StartLabelDetection": {
                        "Type": "Task",
                        "Parameters": {
                          "Video": {
                            "S3Object": {
                              "Bucket": video_src_bucket_name,
                              "Name.$": "$.Key"
                            }
                          },
                          "NotificationChannel": {
                            "RoleArn": rekognition_service_role_arn,
                            "SnsTopicArn": rekognition_sns_topic_arn
                          },
                          "MinConfidence": 95
                        },
                        "Resource": "arn:aws:states:::aws-sdk:rekognition:startLabelDetection",
                        "ResultPath": "$.Rekognition",
                        "Next": "Wait for LabelDetection Callback"
                      },
                      "Wait for LabelDetection Callback": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::aws-sdk:dynamodb:putItem.waitForTaskToken",
                        "Parameters": {
                          "TableName": "rekognitionJobTracker",
                          "Item": {
                            "Key": {
                              "S.$": "$.Key"
                            },
                            "video": {
                              "S.$": "$.Key"
                            },
                            "jobid": {
                              "S.$": "$.Rekognition.JobId"
                            },
                            "jobName": {
                              "S": "Label Detection"
                            },
                            "processingStatus": {
                              "S": "processing"
                            },
                            "taskToken": {
                              "S.$": "$$.Task.Token"
                            }
                          }
                        },
                        "ResultPath": "$.DynamoDBResult",
                        "Next": "GetLabelDetection"
                      },
                      "GetLabelDetection": {
                        "Type": "Task",
                        "Parameters": {
                          "AggregateBy": "SEGMENTS",
                          "JobId.$": "$.Rekognition.JobId",
                          "MaxResults": 1000,
                          "SortBy": "NAME"
                        },
                        "Resource": "arn:aws:states:::aws-sdk:rekognition:getLabelDetection",
                        "ResultPath": "$.Results",
                        "Next": "Update Label Detection Status"
                      },
                      "Update Label Detection Status": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::dynamodb:updateItem",
                        "Parameters": {
                          "TableName": "rekognitionJobTracker",
                          "Key": {
                            "video": {
                              "S.$": "$.Key"
                            },
                            "jobid": {
                              "S.$": "$.Rekognition.JobId"
                            }
                          },
                          "UpdateExpression": "SET processingStatus = :processingStatus",
                          "ExpressionAttributeValues": {
                            ":processingStatus": {
                              "S.$": "$.Results.JobStatus"
                            }
                          }
                        },
                        "Next": "Write Rekognition Label Detection Results to File",
                        "ResultPath": "$.DynamoDBResult"
                      },
                      "Write Rekognition Label Detection Results to File": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::lambda:invoke",
                        "OutputPath": "$.Payload",
                        "Parameters": {
                          "FunctionName": label_detection_lambda_arn,
                          "Payload": {
                            "executionId.$": "$$.Execution.Name",
                            "prefix": "labels",
                            "Key.$": "$.Key",
                            "Results.$": "$.Results"
                          }
                        },
                        "Retry": [
                          {
                            "ErrorEquals": [
                              "Lambda.ServiceException",
                              "Lambda.AWSLambdaException",
                              "Lambda.SdkClientException",
                              "Lambda.TooManyRequestsException"
                            ],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 6,
                            "BackoffRate": 2
                          }
                        ],
                        "End": True
                      }
                    }
                  },
                  "Label": "LabelDetectionMap",
                  "MaxConcurrency": 10,
                  "ItemReader": {
                    "Resource": "arn:aws:states:::s3:listObjectsV2",
                    "Parameters": {
                      "Bucket": video_src_bucket_name
                    },
                    "ReaderConfig": {}
                  },
                  "Next": "Create/Update VideoContentCatalog"
                },
                "Create/Update VideoContentCatalog": {
                  "Type": "Task",
                  "Parameters": {
                    "Name": glue_crawler_name
                  },
                  "Resource": "arn:aws:states:::aws-sdk:glue:startCrawler",
                  "Next": "Move Proccessed Files"
                },
                "Move Proccessed Files": {
                  "Type": "Map",
                  "ItemProcessor": {
                    "ProcessorConfig": {
                      "Mode": "DISTRIBUTED",
                      "ExecutionType": "EXPRESS"
                    },
                    "StartAt": "Lambda Invoke",
                    "States": {
                      "Lambda Invoke": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::lambda:invoke",
                        "OutputPath": "$.Payload",
                        "Parameters": {
                          "FunctionName": processed_file_lambda_arn,
                          "Payload": {
                            "executionId.$": "$$.Execution.Name",
                            "Bucket": video_src_bucket_name,
                            "Items.$": "$.Items"
                          }
                        },
                        "Retry": [
                          {
                            "ErrorEquals": [
                              "Lambda.ServiceException",
                              "Lambda.AWSLambdaException",
                              "Lambda.SdkClientException",
                              "Lambda.TooManyRequestsException"
                            ],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 6,
                            "BackoffRate": 2
                          }
                        ],
                        "End": True
                      }
                    }
                  },
                  "End": True,
                  "Label": "MoveProccessedFiles",
                  "MaxConcurrency": 1000,
                  "ItemReader": {
                    "Resource": "arn:aws:states:::s3:listObjectsV2",
                    "Parameters": {
                      "Bucket": video_src_bucket_name
                    }
                  },
                  "ItemBatcher": {
                    "MaxItemsPerBatch": 10
                  }
                  
                }
              }
        }
        
        return asl
            
            
