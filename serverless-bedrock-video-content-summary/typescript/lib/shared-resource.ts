import {
    Stack,
    StackProps,
    aws_ssm as ssm, 
    aws_dynamodb as dynamodb, 
    aws_sns as sns,
    aws_sns_subscriptions as snsSub,
    aws_mediaconvert as mediaconvert,
    aws_s3 as s3,
    RemovalPolicy
  } from 'aws-cdk-lib';
  import { Construct } from 'constructs';

  export interface SharedResourcesStackProps extends StackProps {
    subEmail: string;
  }

  export class SharedResourcesStack extends Stack {

    constructor(scope: Construct, id: string, props: SharedResourcesStackProps) {
      super(scope, id, props);

      // DDB for Video information
      const videoTable = new dynamodb.Table(this, 'VideoTable', {
        partitionKey: { 
          name: 'video_id', 
          type: dynamodb.AttributeType.STRING 
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
        removalPolicy: RemovalPolicy.DESTROY
      });
      
      // Notification topic to receive video id and job status
      const snsNotificationTopic = new sns.Topic(this, 'NotificationTopic');
      snsNotificationTopic.addSubscription(new snsSub.EmailSubscription(props.subEmail));

      // MediaConvert Queue
      const vodQueue = new mediaconvert.CfnQueue(this, 'MyCfnQueue',  {
        name: 'VoD-Queue',
        pricingPlan: 'ON_DEMAND',
        status: 'ACTIVE',
      });

      // cors rule for s3 bucket
      const corsRules: s3.CorsRule[] = [{
        allowedMethods: [s3.HttpMethods.PUT,s3.HttpMethods.POST,s3.HttpMethods.GET,s3.HttpMethods.HEAD,s3.HttpMethods.DELETE],
        allowedOrigins: ['*'], // Ideally, you should narrow this down to your specific domain
        allowedHeaders: ['*'],
        maxAge: 3000,
        exposedHeaders: [
          'x-amz-server-side-encryption',
          'x-amz-request-id',
          'x-amz-id-2',
          'ETag',
        ],
        id: 'AllowUploadsFromWebApp',
      }];


      //s3 bucket for upload
      const sourceBucket = new s3.Bucket(this, 'SourceBucket', {
        encryption: s3.BucketEncryption.KMS_MANAGED,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        enforceSSL: true,
        cors: corsRules,
        removalPolicy: RemovalPolicy.DESTROY
      });

      // s3 bucket as destination to receive converted video
      const destBucket = new s3.Bucket(this, 'DestinationBucket', {
        encryption: s3.BucketEncryption.KMS_MANAGED,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        enforceSSL: true,
        cors: corsRules,
        removalPolicy: RemovalPolicy.DESTROY
      });

      // ssm parameter store for shared resource references
      new ssm.StringParameter(this, 'VidoeTableName', {
        parameterName: '/vod/shared/ddb-table-name',
        description: 'Shared video DDB table name',
        stringValue: videoTable.tableName
      });

      new ssm.StringParameter(this, 'NotificationTopicArn',{
        parameterName: '/vod/shared/notification-topic-arn',
        description: 'Shared SNS notification topic ARN',
        stringValue: snsNotificationTopic.topicArn
      });

      new ssm.StringParameter(this, 'MediaConvertQueueName',{
        parameterName: '/vod/shared/mediaconvert-queue-name',
        description: 'MediaConvert queue name',
        stringValue: vodQueue.attrName
      });

      new ssm.StringParameter(this, 'SourceBucketName',{
        parameterName: '/vod/shared/source-bucket-name',
        description: 'Shared S3 source bucket name',
        stringValue: sourceBucket.bucketName
      });

      new ssm.StringParameter(this, 'DestBucketName',{
        parameterName: '/vod/shared/dest-bucket-name',
        description: 'Destination S3 source bucket name',
        stringValue: destBucket.bucketName
      });

    }
}