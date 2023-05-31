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
    aws_sns_subscriptions as subscriptions,
    aws_lambda_python_alpha as python_alpha,
    aws_s3_deployment as s3deploy
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
        sfn_log_group_name = "/aws/vendedlogs/states/ProcessVideoContentStateMachine-" + account + '-' + region + '-Logs'
        # Define cloudwatch log group for Step Function logs
        step_function_log_group = logs.LogGroup(self, "StepFunctionLogGroup", log_group_name=sfn_log_group_name, removal_policy=RemovalPolicy.DESTROY)
        
        # create amazon sns  topic for rekognition process notifications
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
        videos_for_processing_bucket=s3.Bucket(self, source_bucket, bucket_name=source_bucket, removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        
        #stage the sample files for processing
        s3deploy.BucketDeployment(self, "DeployVideoSamples",
        sources=[s3deploy.Source.asset("./resources/videos")],
        destination_bucket=videos_for_processing_bucket)
        
        video_processed_bucket = "videos-processed-" + account + '-' + region
        processed_bucket=s3.Bucket(self, video_processed_bucket, bucket_name=video_processed_bucket, removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        
        video_metadata_lake_bucket = 'video-metadata-lake-' + account + '-' + region
        data_lake_bucket=s3.Bucket(self, video_metadata_lake_bucket, bucket_name=video_metadata_lake_bucket, removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        
        # create dynamodb table
        dynamo_db_table_name ="rekognition-job-tracker"
        rekognition_job_tracker_db_tbl =dynamo_db.Table(
            self, dynamo_db_table_name, table_name=dynamo_db_table_name, removal_policy=RemovalPolicy.DESTROY,
            partition_key=dynamo_db.Attribute(
                name="video-name",
                type=dynamo_db.AttributeType.STRING
                ),
            sort_key=dynamo_db.Attribute(
              name="jobid",
              type=dynamo_db.AttributeType.STRING
              ),
            billing_mode=dynamo_db.BillingMode.PAY_PER_REQUEST
            )
        
        rekognition_job_tracker_db_tbl.add_global_secondary_index(index_name='jobid-index',
        partition_key=dynamo_db.Attribute(name='jobid', type=dynamo_db.AttributeType.STRING)
        )
        index_resource_name='arn:aws:dynamodb:' + region + ':' + account + ':table/' + dynamo_db_table_name + '/index/jobid-index'
        
        # create role for callback lambda function
        lambda_callback_role = iam.Role(self, id='state-machine-callback-lambda-role',
          assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
          role_name='state-machine-callback-lambda-role',
          managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')]
        )
        
        lambda_callback_role.add_to_policy(iam.PolicyStatement(
          resources=[index_resource_name],
          actions=["dynamodb:Query"]))
        
        lambda_callback_role.add_to_policy(iam.PolicyStatement(
          resources=[rekognition_job_tracker_db_tbl.table_arn],
          actions=["dynamodb:GetItem"]))
            
        lambda_callback_role.add_to_policy(iam.PolicyStatement(
          resources=["*"],
          actions=["states:SendTaskSuccess", "states:SendTaskFailure"]))
        
        # create lambda functions
        state_machine_callback_lambda = lambda_.Function(self, "stateMachineCallback",
            code=lambda_.Code.from_asset("./functions/stateMachineCallback"),
            handler="app.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            environment={
              "dynamo_db_table":dynamo_db_table_name
            },
            role=lambda_callback_role,
            timeout=Duration.minutes(5)
        )
        
        self.topic.add_subscription(subscriptions.LambdaSubscription(state_machine_callback_lambda))
        
        
        # create roles for lambdas
        wrkflow_lambda_role = iam.Role(self, id='rekognition-wrkflw-lambda-role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            role_name='rekognition-wrkflw-lambda-role',
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')]
        )
        
        wrkflow_lambda_role.add_to_policy(iam.PolicyStatement(
            resources=[f"{data_lake_bucket.bucket_arn}/*",
            f"{videos_for_processing_bucket.bucket_arn}/*"
            
            ],
            actions=["s3:PutObject",
            "s3:PutObjectTagging",
            "s3:GetObject",
            "s3:GetObjectTagging"]
            )
        )
        
        post_wrkflw_lambda_role = iam.Role(self, id='post-rekognition-wrkflw-lambda-role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            role_name='post-rekognition-post-wrkflw-lambda-role',
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')]
        )
        
        post_wrkflw_lambda_role.add_to_policy(iam.PolicyStatement(
            resources=[f"{data_lake_bucket.bucket_arn}/*",
            f"{processed_bucket.bucket_arn}/*",
            f"{videos_for_processing_bucket.bucket_arn}/*"
            ],
            actions=[
                "s3:PutObject",
                "s3:GetObject",
                "s3:GetObjectTagging",
                "s3:DeleteObject",
                "s3:PutObjectTagging",
                "s3:PutObjectAcl"
            ]
            )
        )
        
        
        # define lambdas from assets
        write_segment_data_lambda = python_alpha.PythonFunction(self, "write-segment-data",
            entry="./functions/writeSegmentData",
            #code=lambda_.Code.from_asset("./functions/writeSegmentData"),
            index="app.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            #layers = [pandaLayer],
            environment={
                "video_metadata_lake_bucket":video_metadata_lake_bucket,
                "video_src_bucket":source_bucket
            },
            role=wrkflow_lambda_role,
            timeout=Duration.minutes(5)
        )
        
        
        write_label_data_lambda =python_alpha.PythonFunction(self, "write-label-data",
            #code=lambda_.Code.from_asset("./functions/writeLabelData"),
            entry="./functions/writeLabelData",
            index="app.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            #layers=[pandaLayer],
            environment={
                "video_metadata_lake_bucket":video_metadata_lake_bucket,
                "video_src_bucket":source_bucket
            },
            role=wrkflow_lambda_role,
            timeout=Duration.minutes(5)
        )
        
        write_content_moderated_lambda=python_alpha.PythonFunction(self, "write-content-moderated-data",
            #code=lambda_.Code.from_asset("./functions/writeContentModeratedData"),
            entry="./functions/writeContentModeratedData",
            index="app.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            #layers=[pandaLayer],
            environment={
                "video_metadata_lake_bucket":video_metadata_lake_bucket,
                "video_src_bucket":source_bucket
            },
            role=wrkflow_lambda_role,
            timeout=Duration.minutes(5)
        )
        
        move_processed_lambda=lambda_.Function(self, "move-processed-files",
            code=lambda_.Code.from_asset("./functions/moveProcessedFiles"),
            handler="app.lambda_handler",
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
        stepfunctions_service_principal = "states.amazonaws.com"
        
        role = iam.Role(self, "stepfunction-rekognition-workflow-role",
            managed_policies=[
              iam.ManagedPolicy.from_aws_managed_policy_name('AmazonRekognitionFullAccess'),
              iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'),
              #iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsFullAccess')
              ],
            assumed_by=iam.ServicePrincipal(stepfunctions_service_principal),
        )
        
        role.add_to_policy(iam.PolicyStatement(
          resources=["*"],
          actions=[
            "logs:CreateLogDelivery",
                "logs:CreateLogStream",
                "logs:GetLogDelivery",
                "logs:UpdateLogDelivery",
                "logs:DeleteLogDelivery",
                "logs:ListLogDeliveries",
                "logs:PutLogEvents",
                "logs:PutResourcePolicy",
                "logs:DescribeResourcePolicies",
                "logs:DescribeLogGroups"
            ]
          ))
        
        role.add_to_policy(iam.PolicyStatement(
          resources=[rekognition_service_role.role_arn],
          actions=["iam:GetRole","iam:PassRole"]
          )
        )
        
        role.add_to_policy(iam.PolicyStatement(
          resources=[
            write_content_moderated_lambda.function_arn,
            write_label_data_lambda.function_arn,
            write_segment_data_lambda.function_arn,
            move_processed_lambda.function_arn
            ],
          actions=["lambda:InvokeFunction"]
          )
        )
        
        crawler_arn = f"arn:aws:glue:{region}:{account}:crawler/video_content_data_crawler"
        role.add_to_policy(iam.PolicyStatement(
          resources=[crawler_arn],
          actions=["glue:StartCrawler"]
          )
        )
        
        role.add_to_policy(iam.PolicyStatement(
          resources=["*"],
          actions=[
                "events:PutTargets",
                "events:DescribeRule",
                "events:PutRule",
                "states:StartExecution"
                ]
          )
        )
        
        role.add_to_policy(iam.PolicyStatement(
          resources=[f"{rekognition_job_tracker_db_tbl.table_arn}"],
          actions=["dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem"]
                )
        )
        
        # create state machine
        asl = self.build_video_processing_workflow_definition(
            write_content_moderated_lambda.function_arn,
            write_label_data_lambda.function_arn,
            write_segment_data_lambda.function_arn,
            move_processed_lambda.function_arn,
            source_bucket,
            VIDEO_CONTENT_DATA_CRAWLER_NAME,
            self.topic.topic_arn,
            rekognition_service_role.role_arn,
            dynamo_db_table_name
        )
        
       # _role = role.without_policy_updates()
        
        statemachine = sfn.CfnStateMachine(
            self, "ProcessVideoContentStateMachine",
            definition=asl,
            role_arn=role.role_arn,
            logging_configuration = sfn.CfnStateMachine.LoggingConfigurationProperty(
                destinations=[sfn.CfnStateMachine.LogDestinationProperty(
                  cloud_watch_logs_log_group=sfn.CfnStateMachine.CloudWatchLogsLogGroupProperty(
                    log_group_arn=step_function_log_group.log_group_arn
                  )
                )],
                level="ALL"
            )
        )
        
        

        
    def build_video_processing_workflow_definition(
        self, 
        content_moderated_lambda_arn,
        label_detection_lambda_arn,
        segment_detection_lambda_arn,
        processed_file_lambda_arn, 
        video_src_bucket_name,
        glue_crawler_name,
        rekognition_sns_topic_arn,
        rekognition_service_role_arn,
        rekognition_job_tracker_db_name):
                
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
                          "TableName": rekognition_job_tracker_db_name,
                          "Item": {
                            "Key": {
                              "S.$": "$.Key"
                            },
                            "video-name": {
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
                          "TableName": rekognition_job_tracker_db_name,
                          "Key": {
                            "video-name": {
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
                            "executionId.$": "$$.Execution.Name",
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
                              "Bucket": video_src_bucket_name,
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
                          "TableName": rekognition_job_tracker_db_name,
                          "Item": {
                            "Key": {
                              "S.$": "$.Key"
                            },
                            "video-name": {
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
                          "TableName": rekognition_job_tracker_db_name,
                          "Key": {
                            "video-name": {
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
                          "TableName": rekognition_job_tracker_db_name,
                          "Item": {
                            "Key": {
                              "S.$": "$.Key"
                            },
                            "video-name": {
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
                          "TableName": rekognition_job_tracker_db_name,
                          "Key": {
                            "video-name": {
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
                    "StartAt": "MoveProcessedFiles",
                    "States": {
                      "MoveProcessedFiles": {
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
            
            
