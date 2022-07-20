import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class TextractIntegrationStepFunctionStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const bucket = new cdk.aws_s3.Bucket(this, 'PayloadBucket', {
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
    });

    new cdk.aws_s3_deployment.BucketDeployment(this, 'Add Sample PDF', {
      sources: [cdk.aws_s3_deployment.Source.asset('./resources/sampleData/')],
      destinationBucket: bucket,
    });

    const stateMachine = this.createStepFunction(bucket);
    stateMachine.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        resources: [`${bucket.bucketArn}`, `${bucket.bucketArn}/*`],
        actions: ['s3:getobject', 's3:putobject', 's3:listobject*'],
      }),
    );
  }

  private createStepFunction(bucket: cdk.aws_s3.Bucket) {
    const topic = new cdk.aws_sns.Topic(this, 'FlowTopic');
    const successTopic = new cdk.aws_sns.Topic(this, 'SuccessTopic');
    const queue = new cdk.aws_sqs.Queue(this, 'Queue', {
      fifo: true,
      contentBasedDeduplication: true,
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
            'S3Object.$': '$.Input',
          },
          NotificationChannel: {
            RoleArn: textractDoneRole.roleArn,
            SnsTopicArn: topic.topicArn,
          },
          OutputConfig: {
            S3Bucket: bucket.bucketName,
            S3Prefix: 'output',
          },
        },
      });

    const waitAndCallBack = new cdk.aws_stepfunctions.CustomState(
      this,
      'Wait for Textract Callback',
      {
        stateJson: {
          Next: 'Notify Success',
          Type: 'Task',
          Resource: 'arn:aws:states:::sqs:sendMessage.waitForTaskToken',
          Parameters: {
            QueueUrl: queue.queueUrl,
            'MessageGroupId.$': '$.Result.JobId',
            MessageBody: {
              MessageTitle:
                'Task started by Step Functions. Waiting for callback with task token.',
              'TaskToken.$': '$$.Task.Token',
            },
          },
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
      .next(waitAndCallBack)
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
    queue.grantSendMessages(stateMachine);

    this.createCallBackFunction(queue, topic, stateMachine);
    return stateMachine;
  }

  private createCallBackFunction(
    queue: cdk.aws_sqs.Queue,
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
          SQS_QUEUE_URL: queue.queueUrl,
        },
      },
    );
    topic.addSubscription(
      new cdk.aws_sns_subscriptions.LambdaSubscription(callBackFunction),
    );
    queue.grantConsumeMessages(callBackFunction);
    stateMachine.grantTaskResponse(callBackFunction);
  }
}
