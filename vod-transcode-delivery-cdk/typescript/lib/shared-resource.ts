import {
    Stack,
    StackProps,
    aws_ssm as ssm, 
    aws_dynamodb as dynamodb, 
    aws_sns as sns,
    aws_sns_subscriptions as snsSub,
    aws_mediaconvert as mediaconvert,

  } from "aws-cdk-lib";
  import { Construct } from "constructs";

  export interface SharedResourcesStackProps extends StackProps {
    subEmail: string;
  }

  export class SharedResourcesStack extends Stack {
    public readonly videoTable: dynamodb.Table;
    public readonly snsNotificationTopic: sns.Topic;

    constructor(scope: Construct, id: string, props: SharedResourcesStackProps) {
      super(scope, id, props);
      // DDB for Video information
      const videoTable = new dynamodb.Table(this, "VideoTable", {
        partitionKey: { 
          name: "video_id", 
          type: dynamodb.AttributeType.STRING 
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        encryption: dynamodb.TableEncryption.AWS_MANAGED,
      });
      
      // Notification
      const snsNotificationTopic = new sns.Topic(this, "NotificationTopic");

      snsNotificationTopic.addSubscription(new snsSub.EmailSubscription(props.subEmail));

      // MediaConvert Queue
      const vodQueue = new mediaconvert.CfnQueue(this, 'MyCfnQueue',  {
        name: 'VoD-Queue',
        pricingPlan: 'ON_DEMAND',
        status: 'ACTIVE',
      });
      
      // ssm parameter store 
      new ssm.StringParameter(this, "VidoeTableName", {
        parameterName: "/vod/shared/ddb-table-name",
        description: "Shared video DDB table name",
        stringValue: videoTable.tableName
      });

      new ssm.StringParameter(this, "NotificationTopicArn",{
        parameterName: "/vod/shared/notification-topic-arn",
        description: "Shared SNS notification topic ARN",
        stringValue: snsNotificationTopic.topicArn
      });

      new ssm.StringParameter(this, "MediaConvertQueueName",{
        parameterName: "/vod/shared/mediaconvert-queue-name",
        description: "Shared SNS notification topic ARN",
        stringValue: vodQueue.attrName
      });

      new ssm.StringParameter(this, "MediaConvertQueueArn",{
        parameterName: "/vod/shared/nmediaconvert-queue-arn",
        description: "Shared SNS notification topic ARN",
        stringValue: vodQueue.attrArn
      });

    }
}