import {
  Stack,
  StackProps,
  aws_dynamodb as dynamodb,
  aws_iam as iam,
  aws_s3 as s3,
  aws_s3_notifications as s3n,
  aws_sns as sns,
  aws_lambda as lambda,
  aws_mediaconvert as mediaconvert,
  aws_stepfunctions as sfn,
  aws_stepfunctions_tasks as tasks,
  aws_ssm as ssm,
  Duration,
  CfnOutput,
} from "aws-cdk-lib";
import { Construct } from "constructs";

export class TranscodeWorkflowStack extends Stack {
  public readonly assestBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    // S3 destination bucket for transcoded HLS video.
    const destBucket = new s3.Bucket(this, "DestinationBucket", {
      encryption: s3.BucketEncryption.KMS_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true
    });

    this.assestBucket = destBucket
    
    // S3 source bucket for original video upload.
    const sourceBucket = new s3.Bucket(this, "SourceBucket", {
      encryption: s3.BucketEncryption.KMS_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true
    });

    // Archive bucket 
    const archiveBucket = new s3.Bucket(this, "ArchiveBucket",{ 
      encryption: s3.BucketEncryption.KMS_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true
    });
    

    // DDB from shared resources 
    const ddbTableName = ssm.StringParameter.valueForStringParameter(this ,"/vod/shared/ddb-table-name");

    const videoTable = dynamodb.Table.fromTableName(this, "VideoTable", ddbTableName)

    // Lambda exec roles
    const inTakeFunctionExecRole = new iam.Role(this, "InTakeFunctionRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
    });
    inTakeFunctionExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AWSStepFunctionsFullAccess"));
    inTakeFunctionExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AWSLambdaExecute"));

    const jobSubmitFunctionExecRole = new iam.Role(this, "jobSubmitFunctionRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
    })
    jobSubmitFunctionExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AWSElementalMediaConvertFullAccess"));
    jobSubmitFunctionExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AWSLambdaExecute"));

    const getConvertJobStatusFunctionExecRole = new iam.Role(this, "GetConvertJobStatusFunctionExecRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
    });
    getConvertJobStatusFunctionExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AWSElementalMediaConvertFullAccess"));
    getConvertJobStatusFunctionExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AWSLambdaExecute"));

    // MediaConvert role
    const meidaConvertRole = new iam.Role(this, "MediaConvertRole", {
      assumedBy: new iam.ServicePrincipal("mediaconvert.amazonaws.com")
    })
    meidaConvertRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonS3FullAccess"))

    meidaConvertRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonAPIGatewayInvokeFullAccess"))


    // Lambda for archiving. 
    const archiveLambda = new lambda.Function(this, "VOD-Archive", {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: "app.lambda_handler",
      code: lambda.Code.fromAsset("./functions/archive"),
      environment: {
        "ARCHIVE_BUCKET": archiveBucket.bucketName
      },
      timeout: Duration.seconds(15)
    });

    archiveLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["s3:PutObject",
        "s3:PutObjectRetention"],
        effect: iam.Effect.ALLOW,
        resources: [
          archiveBucket.bucketArn,
          archiveBucket.bucketArn+"/*"
        ],
      }),
    );
    
    // Lambda get the convert job status
    const getJobStatusLambda = new lambda.Function(this, "VOD-GetJobStatus", {
      code: lambda.Code.fromAsset("./functions/getConvertJobStatus"),
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: "app.lambda_handler",
      role: getConvertJobStatusFunctionExecRole,
      timeout: Duration.seconds(15)
    });
    const queueName = ssm.StringParameter.valueForStringParameter(this ,"/vod/shared/mediaconvert-queue-name");

    // Job submit lambda take input from sfn
    const jobSubmit = new lambda.Function(this, "VOD-JobSubmit", {
      code: lambda.Code.fromAsset("./functions/jobSubmit"),
      handler: "app.lambda_handler",
      runtime: lambda.Runtime.PYTHON_3_9,
      role: jobSubmitFunctionExecRole,
      environment: {
        "DEST_BUCKET": destBucket.bucketName,
        "MEDIA_CONVERT_ROLE": meidaConvertRole.roleArn,
        "CONVERT_QUEUE": queueName
      },
      timeout: Duration.seconds(15)

    });

    // Notification SNS topic from Shared Resources
    const snsTopicArn = ssm.StringParameter.valueForStringParameter(this, "/vod/shared/notification-topic-arn");

    const snsNotificationTopic = sns.Topic.fromTopicArn(this, "NotificationTopic", snsTopicArn)

    // build SFN statemachine tasks 
    const transcodeTask = new tasks.LambdaInvoke(this, "MediaConvert Transcode", {
      lambdaFunction: jobSubmit,
      payload: sfn.TaskInput.fromJsonPathAt("$")
    });

    const getJobStatusTask = new tasks.LambdaInvoke(this, "Get MediaConvert Transcode Status",{
      lambdaFunction: getJobStatusLambda,
      payload: sfn.TaskInput.fromJsonPathAt("$.Payload")
    });

    const archiveTask = new tasks.LambdaInvoke(this, "Archive original video", {
      lambdaFunction: archiveLambda,
      payload: sfn.TaskInput.fromJsonPathAt("$.Payload")
    });

    // SNS pub task 
    const snsPublishTask = new tasks.SnsPublish(this, "Push Notification", {
      topic: snsNotificationTopic,
      message: sfn.TaskInput.fromJsonPathAt("$.Payload")
    });

    const isConvertJobComplete = new sfn.Choice(this, "Is Meida Convert job Complete?");
    const isConvertJobCompleteCondition = sfn.Condition.stringEquals("$.Payload.job_status", "COMPLETE");

    const sfnWait5S = new sfn.Wait(this, "wait 5 sec", {
      time: sfn.WaitTime.duration(Duration.seconds(5))
    })

    const ddbPutItemTask = new tasks.DynamoPutItem(this, "DDBPutItem", {
      table: videoTable,
      item:{
        video_id: tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt("$.invocation_id")),
        video_name: tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt("$.results[0].videoName")),
        job_status: tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt("$.job_status")),
      },
      inputPath: sfn.JsonPath.stringAt("$.Payload")
    });
    const parallel = new sfn.Parallel(this, "parallel update ddb, and pub sns");

    parallel.branch(ddbPutItemTask)
    parallel.branch(archiveTask);
    parallel.branch(snsPublishTask);
    const chain = sfn.Chain.start(transcodeTask).next(getJobStatusTask).next(isConvertJobComplete.when(
      isConvertJobCompleteCondition,parallel
    ).otherwise(sfnWait5S.next(getJobStatusTask)));

    const sm = new sfn.StateMachine(this, "TranscodeWorkflow", {
      definition: chain
    });
    
    // Ingess lambda function get s3 bucket notification and trigger SFN

    const ingestFunction = new lambda.Function(this, "VOD-IngestFunction",{
      code: lambda.Code.fromAsset("./functions/ingest"),
      handler: "app.lambda_handler",
      runtime: lambda.Runtime.PYTHON_3_9,
      environment: {
        "SFN_ARN": sm.stateMachineArn
      },
      role: inTakeFunctionExecRole,
      timeout: Duration.seconds(15)
    });

    // add S3 notification
    sourceBucket.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.LambdaDestination(ingestFunction));

    // outputs 
    new CfnOutput(this, "SourceS3Bucket", {
      value: sourceBucket.bucketName,
      description: "Source Bucket Name"
    })
  }
}
