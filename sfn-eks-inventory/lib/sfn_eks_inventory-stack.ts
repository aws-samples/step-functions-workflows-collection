import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import path = require('path');
// import * as sqs from 'aws-cdk-lib/aws-sqs';

export class SfnEksInventoryStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // create s3 bucket with default serverside encryption
    const inventoryBucket = new cdk.aws_s3.Bucket(this, 'InventoryBucket', {
      encryption: cdk.aws_s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // setup a python 3.10 lambda function
    const pythonFunction = new cdk.aws_lambda.Function(this, 'PythonFunction', {
      code: cdk.aws_lambda.Code.fromAsset(
        path.join(__dirname, '../src/eksInventory'),
      ),
      handler: 'main.handler',
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_10,
      memorySize: 512,
      timeout: cdk.Duration.seconds(300),
    });
    pythonFunction.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: ['sts:AssumeRole'],
        resources: ['*'],
      }),
    );

    const stateMachineName = 'EksInventory';
    const sfn = new cdk.aws_stepfunctions.StateMachine(
      this,
      'StateMachineFromFile',
      {
        stateMachineName: stateMachineName,
        definitionBody: cdk.aws_stepfunctions.DefinitionBody.fromString(`
        {
          "Comment": "Retrieve AWS Inventory",
          "StartAt": "ListAccounts",
          "States": {
            "ListAccounts": {
              "Type": "Task",
              "Next": "MapAccounts",
              "Parameters": {},
              "Resource": "arn:aws:states:::aws-sdk:organizations:listAccounts"
            },
            "MapAccounts": {
              "Type": "Map",
              "ItemProcessor": {
                "ProcessorConfig": {
                  "Mode": "DISTRIBUTED",
                  "ExecutionType": "STANDARD"
                },
                "StartAt": "Lambda Invoke",
                "States": {
                  "Lambda Invoke": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "OutputPath": "$.Payload",
                    "Parameters": {
                      "Payload.$": "$",
                      "FunctionName": "${pythonFunction.functionName}"
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
                    "End": true
                  }
                }
              },
              "Label": "MapAccounts",
              "MaxConcurrency": 10,
              "ItemsPath": "$.Accounts",
              "ResultSelector": {
                "Clusters.$": "$[*][*]"
              },
              "ResultWriter": {
                "Resource": "arn:aws:states:::s3:putObject",
                "Parameters": {
                  "Bucket": "${inventoryBucket.bucketName}",
                  "Prefix": "data/"
                }
              },
              "End": true
            }
          }
        }
        `),
      },
    );

    pythonFunction.grantInvoke(sfn);
    inventoryBucket.grantReadWrite(sfn);

    sfn.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: ['states:StartExecution'],
        resources: [
          `arn:aws:states:${this.region}:${this.account}:stateMachine:${stateMachineName}`,
          `arn:aws:states:${this.region}:${this.account}:execution:${stateMachineName}/*`,
        ],
      }),
    );

    sfn.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: ['organizations:ListAccounts'],
        resources: ['*'],
      }),
    );
  }
}
