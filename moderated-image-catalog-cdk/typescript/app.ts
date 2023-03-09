import {
  App,
  CfnOutput,
  RemovalPolicy,
  Stack,
  StackProps,
  aws_dynamodb as dynamodb,
  aws_iam as iam,
  aws_kms as kms,
  aws_s3 as s3,
  aws_sns as sns,
  aws_sns_subscriptions as subscriptions,
  aws_stepfunctions as sfn,
  aws_stepfunctions_tasks as tasks,
} from "aws-cdk-lib";
import { Rekognition } from "aws-sdk";
import { Construct } from "constructs";

interface moderatedImageCatalogStackProps extends StackProps {
  moderator_email: string;
}

export class moderatedImageCatalogStack extends Stack {
  constructor(
    scope: Construct,
    id: string,
    props: moderatedImageCatalogStackProps
  ) {
    super(scope, id, props);

    // Create Amazon S3 bucket to which images as input for the workflow will be uploaded.
    const ingestionBucket = new s3.Bucket(this, "IngestionBucket", {
      encryption: s3.BucketEncryption.KMS_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY, // note this parameter deletes the bucket upon stack removal
      autoDeleteObjects: true, // note that this parameter deletes bucket content upon stack removal using an AWS Lambda function
    });

    /**
     * Create Amazon DynamoDB table to which the workflow will write image metadata if it detects objects
     * or text in processed images.
     */
    const catalogTable = new dynamodb.Table(this, "CatalogTable", {
      partitionKey: { name: "Id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: RemovalPolicy.DESTROY, // note this parameter deletes the table and its data upon stack removal
    });

    // Create SNS Topic for moderator notifications
    const sns_key = kms.Alias.fromAliasName(this, "SnsKey", "alias/aws/sns");
    const moderatorNotificationTopic = new sns.Topic(
      this,
      "ModeratorNotificationTopic",
      {
        topicName: "ModeratorNotificationTopic-Typescript",
        masterKey: sns_key,
      }
    );
    // Subscribe moderator to notifications
    moderatorNotificationTopic.addSubscription(
      new subscriptions.EmailSubscription(props.moderator_email)
    );

    // AWS Step Function Definition

    // Step to call Amazon Rekognition to check for inappropriate content
    const checkForInappropriateContent = new tasks.CallAwsService(
      this,
      "Check for inappropriate content",
      {
        service: "rekognition",
        action: "detectModerationLabels",
        parameters: <Rekognition.DetectModerationLabelsRequest>{
          Image: {
            S3Object: {
              Bucket: sfn.JsonPath.stringAt("$.bucket"),
              Name: sfn.JsonPath.stringAt("$.key"),
            },
          },
        },
        resultPath: "$.moderationResult",
        iamResources: ["*"],
        additionalIamStatements: [
          new iam.PolicyStatement({
            actions: ["s3:getObject"],
            resources: [`${ingestionBucket.bucketArn}/*`],
          }),
        ],
      }
    );

    // Choice step depending on whether inappropriate content has been detected
    const hasInappropriateContentBeenDetected = new sfn.Choice(
      this,
      "Inappropriate content detected?"
    );
    const inappropriateContentDetected = sfn.Condition.isPresent(
      "$.moderationResult.ModerationLabels[0]"
    );

    // Step to notify content moderators via SNS topic
    const notifyContentModerators = new tasks.SnsPublish(
      this,
      "Notify content moderators",
      {
        topic: moderatorNotificationTopic,
        integrationPattern: sfn.IntegrationPattern.REQUEST_RESPONSE,
        message: sfn.TaskInput.fromJsonPathAt("$"),
      }
    );

    // Step to call Amazon Rekognition to detect objects
    const detectObjectsInImage = new tasks.CallAwsService(
      this,
      "Detect objects in image",
      {
        service: "rekognition",
        action: "detectLabels",
        parameters: <Rekognition.DetectLabelsRequest>{
          Image: {
            S3Object: {
              Bucket: sfn.JsonPath.stringAt("$.bucket"),
              Name: sfn.JsonPath.stringAt("$.key"),
            },
          },
        },
        resultPath: "$.output",
        iamResources: ["*"],
        additionalIamStatements: [
          new iam.PolicyStatement({
            actions: ["s3:getObject"],
            resources: [`${ingestionBucket.bucketArn}/*`],
          }),
        ],
      }
    );

    // Step to call Amazon Rekognition to detect text
    const detectTextInImage = new tasks.CallAwsService(
      this,
      "Detect text in image",
      {
        service: "rekognition",
        action: "detectText",
        parameters: <Rekognition.DetectTextRequest>{
          Image: {
            S3Object: {
              Bucket: sfn.JsonPath.stringAt("$.bucket"),
              Name: sfn.JsonPath.stringAt("$.key"),
            },
          },
        },
        resultPath: "$.output",
        iamResources: ["*"],
        additionalIamStatements: [
          new iam.PolicyStatement({
            actions: ["s3:getObject"],
            resources: [`${ingestionBucket.bucketArn}/*`],
          }),
        ],
      }
    );

    // Step to record object metadata found in image in DynamoDB table
    const recordObjectsInDatabase = new tasks.DynamoUpdateItem(
      this,
      "Record objects in database",
      {
        table: catalogTable,
        key: {
          Id: tasks.DynamoAttributeValue.fromString(
            sfn.JsonPath.stringAt("$.key")
          ),
        },
        updateExpression: "SET detectedObjects = :o",
        expressionAttributeValues: {
          ":o": tasks.DynamoAttributeValue.fromString(
            sfn.JsonPath.jsonToString(sfn.JsonPath.objectAt("$.output.Labels"))
          ),
        },
      }
    );

    // Step to record text metadata found in image in DynamoDB table
    const recordTextInDatabase = new tasks.DynamoUpdateItem(
      this,
      "Record text in database",
      {
        table: catalogTable,
        key: {
          Id: tasks.DynamoAttributeValue.fromString(
            sfn.JsonPath.stringAt("$.key")
          ),
        },
        updateExpression: "SET detectedText = :t",
        expressionAttributeValues: {
          ":t": tasks.DynamoAttributeValue.fromString(
            sfn.JsonPath.jsonToString(
              sfn.JsonPath.objectAt("$.output.TextDetections")
            )
          ),
        },
      }
    );

    // Parallel step which processes the image in parallel branches
    const processImage = new sfn.Parallel(this, "Process image");
    // Branch #1
    processImage.branch(detectObjectsInImage.next(recordObjectsInDatabase));
    // Branch #2
    processImage.branch(detectTextInImage.next(recordTextInDatabase));

    new sfn.StateMachine(this, "ModeratedImageCatalog", {
      stateMachineName: "moderated-image-catalog-workflow-typescript",
      definition: sfn.Chain.start(
        checkForInappropriateContent.next(
          hasInappropriateContentBeenDetected
            .when(inappropriateContentDetected, notifyContentModerators)
            .otherwise(processImage)
        )
      ),
    });

    // Outputs to assist with testing
    new CfnOutput(this, "IngestionBucketOutput", {
      description: "S3 bucket name",
      value: ingestionBucket.bucketName,
    });
    new CfnOutput(this, "CatalogTableOutput", {
      description: "DynamoDB table name",
      value: catalogTable.tableName,
    });
    new CfnOutput(this, "ModeratorSNSTopicOutput", {
      description: "SNS topic ARN",
      value: moderatorNotificationTopic.topicArn,
    });
  }
}

const app = new App();
new moderatedImageCatalogStack(app, "ModeratedImageCatalogTypescript", {
  moderator_email: "moderator@example.com",
});
app.synth();
