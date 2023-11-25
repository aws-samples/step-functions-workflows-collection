import {
    Stack,
    Duration,
    StackProps,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda,
    aws_sns as sns,
    aws_ssm as ssm,
    aws_dynamodb as dynamodb,
  } from 'aws-cdk-lib';
  import { Construct } from 'constructs';

  export class ErrorHanlderStack extends Stack {

    constructor(scope: Construct, id: string, props: StackProps) {
      super(scope, id, props);

      // SNS topic for notifications
      // Notification SNS topic from Shared Resources
      const snsTopicArn = ssm.StringParameter.valueForStringParameter(this, '/vod/shared/notification-topic-arn');
      const snsNotificationTopic = sns.Topic.fromTopicArn(this, 'NotificationTopic', snsTopicArn)
      
      // DDB table for error message: 
      const errorMsgTable = new dynamodb.Table(this, 'ErrorMsgTable', {
        partitionKey: { 
          name: 'id', 
          type: dynamodb.AttributeType.STRING 
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
      });

      // Error hanlder lambda function
      const errorHandlerFunction = new lambda.Function(this, 'ErrorHander', {
        code: lambda.Code.fromAsset('./functions/errorHandler'),
        runtime: lambda.Runtime.PYTHON_3_9,
        handler: 'app.lambda_handler',
        environment: {
            'TOPIC_ARN': snsNotificationTopic.topicArn,
            'DDB_TABLE_NAME': errorMsgTable.tableName
        },
        timeout: Duration.seconds(15)
      });
      snsNotificationTopic.grantPublish(errorHandlerFunction)
      errorMsgTable.grantReadWriteData(errorHandlerFunction)

      // EventBridge rules for errorHandler function
      const assetFailureRule = new events.Rule(this, 'AssetFailureRule', {
        eventPattern: {
          source: ['aws.mediapackage'],
          detailType: ['MediaPackage Input Notification'],
          detail: {
            event: ['IngestError'],
          },
        },
      });

      // MediaConvert failure notification event
      const mediaConvertFailureRule = new events.Rule(this, 'MediaConvertFailureRule', {
        eventPattern: {
          source: ['aws.mediaconvert'],
          detailType: ['MediaConvert Job State Change'],
          detail: {
            status: ['ERROR'],
          }
        },
      });

      // step function failure event
      const stepFunctionFailureRule = new events.Rule(this, 'StepFunctionFailureRule', {
        eventPattern: {
          source: ['aws.states'],
          detailType: ['Step Functions Execution Status Change'],
          detail: {
            status: ['FAILED'],
          }
        },
      });

      // Add invoke with error handling lambda 
      assetFailureRule.addTarget(new targets.LambdaFunction(errorHandlerFunction));
      mediaConvertFailureRule.addTarget(new targets.LambdaFunction(errorHandlerFunction));
      stepFunctionFailureRule.addTarget(new targets.LambdaFunction(errorHandlerFunction));
    }
}
