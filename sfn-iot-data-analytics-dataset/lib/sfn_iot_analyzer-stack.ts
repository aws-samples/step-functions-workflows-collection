import * as cdk from 'aws-cdk-lib';
import * as iot from '@aws-cdk/aws-iot-alpha';
import { Construct } from 'constructs';

export class SfnIotAnalyzerStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // create sns topic
    const topic = new cdk.aws_sns.Topic(this, 'SfnIotAnalyzerTopic');

    // create s3 bucket with default serverside encryption
    const datasetBucket = new cdk.aws_s3.Bucket(this, 'IotChannelStorage', {
      encryption: cdk.aws_s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const checkpointTable = new cdk.aws_dynamodb.Table(
      this,
      'CheckPointTable',
      {
        partitionKey: {
          name: 'PK1',
          type: cdk.aws_dynamodb.AttributeType.STRING,
        },
        billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        timeToLiveAttribute: 'expiry',
        removalPolicy: cdk.RemovalPolicy.DESTROY,
      },
    );

    const cfnDatastore = new cdk.aws_iotanalytics.CfnDatastore(
      this,
      'TurbineDatastore',
      /* all optional props */ {
        datastoreName: 'windTurbine',
        datastoreStorage: {
          serviceManagedS3: {},
        },
        fileFormatConfiguration: {
          jsonConfiguration: {},
        },
        retentionPeriod: {
          numberOfDays: 90,
          unlimited: false,
        },
        tags: [
          {
            key: 'data',
            value: 'windTurbine',
          },
        ],
      },
    );

    const cfnChannel = new cdk.aws_iotanalytics.CfnChannel(
      this,
      'TurbineChannel',
      {
        channelName: 'turbineChannel',
        channelStorage: {
          serviceManagedS3: {},
        },
        retentionPeriod: {
          numberOfDays: 90,
          unlimited: false,
        },
        tags: [
          {
            key: 'data',
            value: 'windTurbine',
          },
        ],
      },
    );

    const cfnPipeline = new cdk.aws_iotanalytics.CfnPipeline(
      this,
      'TurbinePipeline',
      {
        pipelineActivities: [
          {
            selectAttributes: {
              attributes: ['device_id', 'power_output'],
              name: 'device_details',
              next: 'ChannelActivity',
            },
            channel: {
              name: 'ChannelActivity',
              channelName: cfnChannel.channelName as string,
              next: 'DatastoreActivity',
            },
            datastore: {
              name: 'DatastoreActivity',
              datastoreName: cfnDatastore.datastoreName as string,
            },
          },
        ],
        pipelineName: 'windturbine',
        tags: [
          {
            key: 'data',
            value: 'windTurbine',
          },
        ],
      },
    );

    // create iot topic role
    const iotTopicRole = new cdk.aws_iam.Role(this, 'IotTopicRole', {
      assumedBy: new cdk.aws_iam.ServicePrincipal('iot.amazonaws.com'),
      inlinePolicies: {
        'iot-topic-role-policy': new cdk.aws_iam.PolicyDocument({
          statements: [
            new cdk.aws_iam.PolicyStatement({
              actions: ['iot:Publish'],
              resources: ['*'],
            }),
          ],
        }),
      },
    });

    const cfnTopicRule = new cdk.aws_iot.CfnTopicRule(this, 'MyCfnTopicRule', {
      topicRulePayload: {
        actions: [
          {
            iotAnalytics: {
              channelName: cfnChannel.channelName as string,
              roleArn: iotTopicRole.roleArn,

              // the properties below are optional
              batchMode: false,
            },
          },
        ],
        sql: 'SELECT temp FROM "windTurbine" WHERE severity = "critical"',

        // the properties below are optional
        awsIotSqlVersion: '2016-03-23',
        description: 'description',
        // errorAction: {},
        ruleDisabled: false,
      },

      // the properties below are optional
      ruleName: 'criticalEvents',
      tags: [
        {
          key: 'severity',
          value: 'critical',
        },
      ],
    });

    // dynamodb Table with encryption enabled, PK1 ans primary key and SK1 as sort key
    const table = new cdk.aws_dynamodb.Table(this, 'DataTable', {
      partitionKey: {
        name: 'PK1',
        type: cdk.aws_dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'SK1',
        type: cdk.aws_dynamodb.AttributeType.STRING,
      },
      encryption: cdk.aws_dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // create IAM role that allows iot analytics operations
    const iotAnalyticsDatasetRole = new cdk.aws_iam.Role(
      this,
      'IotAnalyticsRole',
      {
        assumedBy: new cdk.aws_iam.ServicePrincipal(
          'iotanalytics.amazonaws.com',
        ),
        inlinePolicies: {
          'iot-analytics-role-policy': new cdk.aws_iam.PolicyDocument({
            statements: [
              new cdk.aws_iam.PolicyStatement({
                actions: ['iotanalytics:*'],
                resources: ['*'],
              }),
            ],
          }),
        },
      },
    );

    // create IAM role that allows IoT Analytics
    const dataSetRole = new cdk.aws_iam.Role(this, 'DataSetRole', {
      assumedBy: new cdk.aws_iam.ServicePrincipal('iotanalytics.amazonaws.com'),
    });
    datasetBucket.grantReadWrite(dataSetRole);

    const getDatasetFunction = new cdk.aws_lambda_nodejs.NodejsFunction(
      this,
      'GetDatasetFunction',
      {
        entry: 'src/getDatasetFunction/index.ts',
        handler: 'handler',
        runtime: cdk.aws_lambda.Runtime.NODEJS_16_X,
        architecture: cdk.aws_lambda.Architecture.X86_64,
        timeout: cdk.Duration.seconds(30),
        environment: {
          BUCKET: datasetBucket.bucketName,
        },
      },
    );
    datasetBucket.grantWrite(getDatasetFunction);

    const sfn = new cdk.aws_stepfunctions.StateMachine(
      this,
      'StateMachineFromFile',
      {
        stateMachineName: 'IotAnalyticsProcessor',
        definitionBody: cdk.aws_stepfunctions.DefinitionBody.fromString(`
        {
          "Comment": "A description of my state machine",
          "StartAt": "BatchPutMessage",
          "States": {
            "BatchPutMessage": {
              "Type": "Task",
              "Next": "CreateDataset",
              "Parameters": {
                "ChannelName": "${cfnChannel.channelName}",
                "Messages.$": "$.Messages"
              },
              "Resource": "arn:aws:states:::aws-sdk:iotanalytics:batchPutMessage"
            },
            "CreateDataset": {
              "Type": "Task",
              "Next": "CreateDatasetContent",
              "Parameters": {
                "Actions": [
                  {
                    "ActionName": "myaction",
                    "QueryAction": {
                      "SqlQuery": "SELECT device_id, AVG(power_output) as average_power FROM windturbine GROUP BY device_id"
                    }
                  }
                ],
                "ContentDeliveryRules": [ 
                   { 
                      "Destination": { 
                         "S3DestinationConfiguration": { 
                            "Bucket": "${datasetBucket.bucketName}",
                            "Key": "dataset/mydataset/!{iotanalytics:scheduleTime}/!{iotanalytics:versionId}.csv",
                            "RoleArn": "${dataSetRole.roleArn}"
                         }
                      }
                   }
                ],
                "DatasetName": "windturbine"
              },
              "Resource": "arn:aws:states:::aws-sdk:iotanalytics:createDataset",
              "Catch": [
                {
                  "ErrorEquals": [
                    "IoTAnalytics.ResourceAlreadyExistsException"
                  ],
                  "Next": "CreateDatasetContent"
                }
              ]
            },
            "CreateDatasetContent": {
              "Type": "Task",
              "Next": "Wait for Dataset Content creation and Callback Token",
              "Parameters": {
                "DatasetName": "windturbine"
              },
              "Resource": "arn:aws:states:::aws-sdk:iotanalytics:createDatasetContent"
            },
            "Wait for Dataset Content creation and Callback Token": {
              "Next": "GetDatasetContent",
              "Type": "Task",
              "Resource": "arn:aws:states:::aws-sdk:dynamodb:putItem.waitForTaskToken",
              "Parameters": {
                "TableName": "${checkpointTable.tableName}",
                "Item": {
                  "PK1": {
                    "S.$": "$.VersionId"
                  },
                  "TT": {
                    "S.$": "$$.Task.Token"
                  },
                  "STATUS": {
                    "S": "PROCESSING"
                  }
                }
              },
              "TimeoutSeconds": 1800
            },
            "GetDatasetContent": {
              "Type": "Task",
              "Next": "Put Content To S3",
              "Parameters": {
                "DatasetName": "windturbine"
              },
              "Resource": "arn:aws:states:::aws-sdk:iotanalytics:getDatasetContent",
              "Retry": [
                {
                  "ErrorEquals": [
                    "IoTAnalytics.ResourceNotFoundException",
                    "InternalServerError"
                  ],
                  "BackoffRate": 2,
                  "IntervalSeconds": 5,
                  "MaxAttempts": 10
                }
              ],
              "Catch": [
                {
                  "ErrorEquals": [
                    "States.ALL"
                  ],
                  "Next": "Fail"
                }
              ]
            },
            "Put Content To S3": {
              "Type": "Task",
              "Resource": "arn:aws:states:::lambda:invoke",
              "OutputPath": "$.Payload",
              "Parameters": {
                "Payload.$": "$",
                "FunctionName": "${getDatasetFunction.functionName}"
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
              "Next": "Map"
            },
            "Map": {
              "Type": "Map",
              "ItemProcessor": {
                "ProcessorConfig": {
                  "Mode": "DISTRIBUTED",
                  "ExecutionType": "EXPRESS"
                },
                "StartAt": "DynamoDB PutItem",
                "States": {
                  "DynamoDB PutItem": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::dynamodb:putItem",
                    "Parameters": {
                      "TableName": "${table.tableName}",
                      "Item": {
                        "PK1": {
                          "S.$": "$.device_id"
                        },
                        "SK1": {
                          "S.$": "$.device_id"
                        },
                        "PWR": {
                          "S.$": "$.average_power"
                        }
                      }
                    },
                    "End": true
                  }
                }
              },
              "Next": "Success",
              "Label": "Map",
              "MaxConcurrency": 100,
              "ItemReader": {
                "Resource": "arn:aws:states:::s3:getObject",
                "ReaderConfig": {
                  "InputType": "CSV",
                  "CSVHeaderLocation": "FIRST_ROW"
                },
                "Parameters": {
                  "Bucket.$": "$.Bucket",
                  "Key.$": "$.Key"
                }
              }
            },
            "Success": {
              "Type": "Succeed"
            },
            "Fail": {
              "Type": "Fail"
            }
          }
        }
      `),
      },
    );
    topic.grantPublish(sfn);
    table.grantWriteData(sfn);
    datasetBucket.grantRead(sfn);
    checkpointTable.grantWriteData(sfn);
    getDatasetFunction.grantInvoke(sfn);

    sfn.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: [
          'iotanalytics:CreateDataset',
          'iotanalytics:BatchPutMessage',
          'iotanalytics:GetDatasetContent',
          'iotanalytics:CreateDatasetContent',
          'states:StartExecution',
          'states:DescribeExecution',
          'states:StopExecution',
          'iam:PassRole',
        ],
        resources: [
          `arn:aws:iotanalytics:${this.region}:${this.account}:dataset/windturbine`,
          `arn:aws:iotanalytics:${this.region}:${this.account}:channel/turbineChannel`,
          `arn:aws:states:${this.region}:${this.account}:stateMachine:IotAnalyticsProcessor`,
          `arn:aws:states:${this.region}:${this.account}:execution:IotAnalyticsProcessor/*`,
          `${dataSetRole.roleArn}`,
        ],
      }),
    );

    this.createCallBackFunction(checkpointTable, sfn);
  }

  private createCallBackFunction(
    checkpointTable: cdk.aws_dynamodb.Table,
    stateMachine: cdk.aws_stepfunctions.StateMachine,
  ) {
    const callBackFunction = new cdk.aws_lambda_nodejs.NodejsFunction(
      this,
      'CallBackFunction',
      {
        entry: 'src/callBackFunction/index.ts',
        handler: 'handler',
        runtime: cdk.aws_lambda.Runtime.NODEJS_16_X,
        architecture: cdk.aws_lambda.Architecture.X86_64,
        timeout: cdk.Duration.seconds(30),
        environment: {
          DDB_TABLE: checkpointTable.tableName,
        },
      },
    );
    checkpointTable.grantReadWriteData(callBackFunction);
    stateMachine.grantTaskResponse(callBackFunction);

    const rule = new cdk.aws_events.Rule(this, 'rule', {
      eventPattern: {
        source: ['aws.iotanalytics'],
        detailType: ['IoT Analytics Dataset Lifecycle Notification'],
        detail: {
          'dataset-name': ['windturbine'],
          state: ['CONTENT_DELIVERY_SUCCEEDED'],
        },
      },
    });

    rule.addTarget(new cdk.aws_events_targets.LambdaFunction(callBackFunction));
  }
}
