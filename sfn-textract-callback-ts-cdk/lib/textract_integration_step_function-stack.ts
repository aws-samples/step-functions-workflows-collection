import * as cdk from 'aws-cdk-lib';
import { IRuleTarget, Match, Rule, Schedule } from 'aws-cdk-lib/aws-events';
import { Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { EventType } from 'aws-cdk-lib/aws-s3';
import { table } from 'console';
import { Construct } from 'constructs';

export class TextractIntegrationStepFunctionStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const sourceBucket = new cdk.aws_s3.Bucket(this, 'SourceBucket', {
      blockPublicAccess: {
        blockPublicAcls: true,
        blockPublicPolicy: true,
        ignorePublicAcls: true,
        restrictPublicBuckets: true,
      },
      enforceSSL: true,
      publicReadAccess: false,
      encryption: cdk.aws_s3.BucketEncryption.S3_MANAGED,
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      eventBridgeEnabled: true,
    });

    const destinationBucket = new cdk.aws_s3.Bucket(this, 'DestinationBucket', {
      blockPublicAccess: {
        blockPublicAcls: true,
        blockPublicPolicy: true,
        ignorePublicAcls: true,
        restrictPublicBuckets: true,
      },
      enforceSSL: true,
      publicReadAccess: false,
      encryption: cdk.aws_s3.BucketEncryption.S3_MANAGED,
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    new cdk.aws_s3_deployment.BucketDeployment(this, 'Add Sample PDF', {
      sources: [cdk.aws_s3_deployment.Source.asset('./resources/sampleData/')],
      destinationBucket: sourceBucket,
    });

    const stateMachine = this.createStepFunction(
      sourceBucket,
      destinationBucket,
    );
    stateMachine.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        resources: [
          `${sourceBucket.bucketArn}`,
          `${sourceBucket.bucketArn}/*`,
          `${destinationBucket.bucketArn}`,
          `${destinationBucket.bucketArn}/*`,
        ],
        actions: ['s3:getobject', 's3:putobject', 's3:listobject*'],
      }),
    );

    const eventsInvokeSfnRole = new Role(this, 'Role', {
      assumedBy: new ServicePrincipal('events.amazonaws.com'),
      description: 'Allow Execution of States Function from EventBridge',
    });
    eventsInvokeSfnRole.addToPolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: ['states:StartExecution'],
        resources: [stateMachine.stateMachineArn],
      }),
    );

    const stateMachineBind: IRuleTarget = {
      bind: () => ({
        id: '',
        arn: stateMachine.stateMachineArn,
        role: eventsInvokeSfnRole,
      }),
    };

    new Rule(this, 'StartTextractSfn', {
      eventPattern: {
        detailType: ['Object Created'],
        detail: {
          bucket: {
            name: [sourceBucket.bucketName],
          },
        },
        source: ['aws.s3'],
      },
      targets: [stateMachineBind],
    });
  }

  private createStepFunction(
    sourceBucket: cdk.aws_s3.Bucket,
    destinationBucket: cdk.aws_s3.Bucket,
  ) {
    const topic = new cdk.aws_sns.Topic(this, 'FlowTopic');
    const successTopic = new cdk.aws_sns.Topic(this, 'SuccessTopic');
    const table = new cdk.aws_dynamodb.Table(this, 'CheckPointTable', {
      partitionKey: {
        name: 'PK1',
        type: cdk.aws_dynamodb.AttributeType.STRING,
      },
      billingMode: cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: 'expiry',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const logGroup = new cdk.aws_logs.LogGroup(this, 'SfLogs', {
      retention: cdk.aws_logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const textractDoneRole = new cdk.aws_iam.Role(this, 'textractDoneRole', {
      assumedBy: new cdk.aws_iam.ServicePrincipal('textract.amazonaws.com'),
      inlinePolicies: {
        DescribeACMCerts: new cdk.aws_iam.PolicyDocument({
          statements: [
            new cdk.aws_iam.PolicyStatement({
              resources: [topic.topicArn],
              actions: ['sns:Publish'],
            }),
          ],
        }),
      },
    });

    const startDocumentDetection =
      new cdk.aws_stepfunctions_tasks.CallAwsService(this, 'textract', {
        action: 'startDocumentTextDetection',
        service: 'textract',
        iamResources: ['*'],
        resultPath: '$.Result',
        parameters: {
          DocumentLocation: {
            S3Object: {
              'Bucket.$': '$.detail.bucket.name',
              'Name.$': '$.detail.object.key',
            },
          },
          NotificationChannel: {
            RoleArn: textractDoneRole.roleArn,
            SnsTopicArn: topic.topicArn,
          },
          OutputConfig: {
            S3Bucket: destinationBucket.bucketName,
            S3Prefix: 'output',
          },
        },
      });

    const waitForCallBack = new cdk.aws_stepfunctions.CustomState(
      this,
      'Wait for Textract Callback Token',
      {
        stateJson: {
          Next: 'Notify Success',
          Type: 'Task',
          Resource:
            'arn:aws:states:::aws-sdk:dynamodb:putItem.waitForTaskToken',
          Parameters: {
            TableName: table.tableName,
            Item: {
              PK1: {
                'S.$': '$.Result.JobId',
              },
              TT: {
                'S.$': '$$.Task.Token',
              },
              STATUS: {
                S: 'PROCESSING',
              },
            },
          },
          TimeoutSeconds: 1800,
        },
      },
    );

    const notifySuccess = new cdk.aws_stepfunctions_tasks.CallAwsService(
      this,
      'Notify Success',
      {
        action: 'publish',
        service: 'sns',
        iamResources: [successTopic.topicArn],
        resultPath: '$.Result',
        parameters: {
          Message: 'Success',
          TopicArn: successTopic.topicArn,
        },
      },
    );

    const definition = startDocumentDetection
      .next(waitForCallBack)
      .next(notifySuccess);

    const stateMachine = new cdk.aws_stepfunctions.StateMachine(
      this,
      'StateMachine',
      {
        definition: definition,
        stateMachineType: cdk.aws_stepfunctions.StateMachineType.STANDARD,
        logs: {
          destination: logGroup,
          level: cdk.aws_stepfunctions.LogLevel.ALL,
        },
      },
    );
    table.grantReadWriteData(stateMachine);

    this.createCallBackFunction(table, topic, stateMachine);
    return stateMachine;
  }

  private createCallBackFunction(
    table: cdk.aws_dynamodb.Table,
    topic: cdk.aws_sns.Topic,
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
          DDB_TABLE: table.tableName,
        },
      },
    );
    topic.addSubscription(
      new cdk.aws_sns_subscriptions.LambdaSubscription(callBackFunction),
    );
    table.grantReadWriteData(callBackFunction);
    stateMachine.grantTaskResponse(callBackFunction);
  }
}
