import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import path = require('path');

export class SfnBedrockDescribeAssetsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // S3 bucket with encryption enabled and delete contents when removed
    const assetBucket = new cdk.aws_s3.Bucket(this, 'AssetBucket', {
      encryption: cdk.aws_s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const outputBucket = new cdk.aws_s3.Bucket(this, 'OutputBucket', {
      encryption: cdk.aws_s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const claude = cdk.aws_bedrock.FoundationModel.fromFoundationModelId(
      this,
      'Model',
      cdk.aws_bedrock.FoundationModelIdentifier
        .ANTHROPIC_CLAUDE_3_SONNET_20240229_V1_0,
    );

    // setup a python 3.12 lambda function
    const fnDescribeAsset = new cdk.aws_lambda.Function(
      this,
      'PythonFunction',
      {
        code: cdk.aws_lambda.Code.fromAsset(
          path.join(__dirname, '../src/describeAsset'),
        ),
        handler: 'main.handler',
        runtime: cdk.aws_lambda.Runtime.PYTHON_3_12,
        memorySize: 1024,
        timeout: cdk.Duration.seconds(300),
        environment: {
          CLAUDE_MODEL: claude.modelId,
          OUTPUT_BUCKET: outputBucket.bucketName,
        },
      },
    );

    const stateMachineName = 'DescribeAssets';
    const sfn = new cdk.aws_stepfunctions.StateMachine(
      this,
      'StateMachineFromFile',
      {
        stateMachineName: stateMachineName,
        definitionBody: cdk.aws_stepfunctions.DefinitionBody.fromString(`
        {
          "Comment": "Describe Assets",
          "StartAt": "S3 object keys",
          "States": {
            "S3 object keys": {
              "Type": "Map",
              "ItemProcessor": {
                "ProcessorConfig": {
                  "Mode": "DISTRIBUTED",
                  "ExecutionType": "STANDARD"
                },
                "StartAt": "Bedrock Describe Assets",
                "States": {
                  "Bedrock Describe Assets": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "OutputPath": "$.Payload",
                    "Parameters": {
                      "Payload.$": "$",
                      "FunctionName": "${fnDescribeAsset.functionName}"
                    },
                    "Retry": [
                      {
                        "ErrorEquals": [
                          "Lambda.ServiceException",
                          "Lambda.AWSLambdaException",
                          "Lambda.SdkClientException",
                          "Lambda.TooManyRequestsException"
                        ],
                        "IntervalSeconds": 1,
                        "MaxAttempts": 3,
                        "BackoffRate": 2
                      }
                    ],
                    "Next": "PutObject to S3"
                  },
                  "PutObject to S3": {
                    "Type": "Task",
                    "End": true,
                    "Parameters": {
                      "Body.$": "$.text",
                      "Bucket.$": "$.bucket",
                      "Key.$": "$.key"
                    },
                    "Resource": "arn:aws:states:::aws-sdk:s3:putObject"
                  }
                }
              },
              "ItemReader": {
                "Resource": "arn:aws:states:::s3:listObjectsV2",
                "Parameters": {
                  "Bucket.$": "$.Bucket"
                }
              },
              "MaxConcurrency": 1000,
              "Label": "S3objectkeys",
              "End": true,
              "ItemBatcher": {
                "MaxItemsPerBatch": 10
              },
              "ItemSelector": {
                "Bucket.$": "$.Bucket",
                "Data.$": "$$.Map.Item.Value"
              }
            }
          }
        }
        `),
      },
    );

    fnDescribeAsset.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: ['bedrock:InvokeModel'],
        resources: [`${claude.modelArn}`],
      }),
    );

    fnDescribeAsset.grantInvoke(sfn);
    assetBucket.grantRead(fnDescribeAsset);
    assetBucket.grantReadWrite(sfn);
    outputBucket.grantWrite(sfn);

    sfn.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: ['states:StartExecution'],
        resources: [
          `arn:aws:states:${this.region}:${this.account}:stateMachine:${stateMachineName}`,
          `arn:aws:states:${this.region}:${this.account}:execution:${stateMachineName}/*`,
        ],
      }),
    );

    const deployment = new cdk.aws_s3_deployment.BucketDeployment(
      this,
      'DeployFiles',
      {
        sources: [
          cdk.aws_s3_deployment.Source.asset(path.join(__dirname, '../assets')),
        ],
        destinationBucket: assetBucket,
      },
    );
  }
}
