import {
    Stack,
    StackProps,
    CfnCondition,
    Duration,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    aws_s3 as s3,
    aws_mediapackage as mediapackage,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_ssm as ssm,
    aws_sns as sns,
    aws_stepfunctions as sfn, 
    aws_stepfunctions_tasks as tasks,
    custom_resources as cr,
    CustomResource,
    aws_logs as log,
    RemovalPolicy,
    Fn,
    CfnOutput,
  } from "aws-cdk-lib";
  import { Construct } from "constructs";

  export interface DeliverChannelStackProp extends StackProps{
    assetBucket: s3.IBucket;
    enableCdnAuth : boolean
  }

  export class DeliverChannelStack extends Stack {
    constructor(scope: Construct, id: string, props: DeliverChannelStackProp) {
      super(scope, id, props);

      const enableCdnAuthCondition = new CfnCondition(this, 'IsProduction', {
        expression: Fn.conditionEquals(true, props.enableCdnAuth),
      });
      // Logging bucket
      
      const loggingBucket = new s3.Bucket(this, "LoggingBucket", {
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL
      })
      
      // Custom resource for creating secret to auth 
      const createSecretFunctionExecRole = new iam.Role(this, "CreateSecretFunctionExecRole", {
        assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
      });
      createSecretFunctionExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AWSLambdaExecute"));
      createSecretFunctionExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("SecretsManagerReadWrite"));
      
      const createSecretFunction = new lambda.Function(this, "VOD-CreateSecret", {
        code: lambda.Code.fromAsset("./customResource/cdnAuthEnable"),
        handler: "custom-resource.on_event",
        runtime: lambda.Runtime.PYTHON_3_9,
        role: createSecretFunctionExecRole,
        timeout: Duration.seconds(15)

      });

      const createSecretProvider = new cr.Provider(this, "CreateSecretProvider", {
        onEventHandler: createSecretFunction,
        logRetention: log.RetentionDays.ONE_DAY
      });

      const createSecretCustomResource = new CustomResource(this, "CreateSecretCustomResource", {
        serviceToken: createSecretProvider.serviceToken,
        properties: {
          "EnableCdnAuth": props.enableCdnAuth,
        }
      });

      // Secret accessing role for MediaPackage
      const secretAccessingRole = new iam.Role(this, "SecretAccessingRole", {
        assumedBy: new iam.ServicePrincipal("mediapackage.amazonaws.com")
      });

      const secretAccessingPolicy = new iam.Policy(this, "SecretAccessingPolicy", {
        policyName: "SecretAccessingPolicy",
        statements: [
          new iam.PolicyStatement({
            actions: [
              "secretsmanager:GetSecretValue",
              "secretsmanager:DescribeSecret",
              "secretsmanager:ListSecrets",
              "secretsmanager:ListSecretVersionIds"
          ],
          resources: [Fn.conditionIf(enableCdnAuthCondition.logicalId,createSecretCustomResource.getAtt("SecretArn"), "*").toString()]
          }),
          new iam.PolicyStatement({
            actions: [
              "iam:GetRole",
              "iam:PassRole",
            ],
            resources: [secretAccessingRole.roleArn]
          })
        ]
      });

      secretAccessingRole.attachInlinePolicy(secretAccessingPolicy)

      // Create Mediapackage packaging group
      const packagingGroup = new mediapackage.CfnPackagingGroup(this, "HLSGroup",{
        id: "HLSGroup",
        authorization: Fn.conditionIf(
          enableCdnAuthCondition.logicalId,
          {
            secretsRoleArn: secretAccessingRole.roleArn,
            cdnIdentifierSecret: createSecretCustomResource.getAtt("SecretArn")
          },
          Fn.ref("AWS::NoValue")
        )
      });

      packagingGroup.node.addDependency(secretAccessingPolicy)

      // Create mediapackage packaging config
      const packagingConfig = new mediapackage.CfnPackagingConfiguration(this, "HLSConfig",{
        id: "HLSConfig",
        hlsPackage: {
            hlsManifests:[{
            }]
        },
        packagingGroupId: packagingGroup.id
      });
      packagingConfig.addDependency(packagingGroup)

      // Retrive the UUID from secret
      const uuidSecret = secretsmanager.Secret.fromSecretPartialArn(this, "UUIDSecret", createSecretCustomResource.getAtt("SecretArn").toString());

      const uuidSecretValue = uuidSecret.secretValueFromJson("MediaPackageCDNIdentifier")

      // CloudFront distribution for the packaging group
      const distribution = new cloudfront.Distribution(this, "Distribution", {
        defaultBehavior: {
          origin: new origins.HttpOrigin(Fn.select(1,Fn.split("//",packagingGroup.attrDomainName)),{
            customHeaders: {
              "X-MediaPackage-CDNIdentifier":  Fn.conditionIf(enableCdnAuthCondition.logicalId, uuidSecretValue.unsafeUnwrap(),"SomeDummyValue").toString()
            }
          }),
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
        },
        enableLogging: true,
        logBucket: loggingBucket,
      });

      // Get asset bucket
      const assestBucket = props.assetBucket

      // Role for mediapackage access s3 bucket object
      const sourceRole = new iam.Role(this, "SourceRole",{
        assumedBy: new iam.ServicePrincipal("mediapackage.amazonaws.com"),
        description: "source role for mediapackage access asset in S3 bucket"
      });

      const sourcRolePoliyStatement = new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
            "s3:GetObject",
            "s3:GetObjectAcl",
            "s3:GetObjectTagging",
            "s3:GetObjectTorrent",
            "s3:GetObjectVersion",
            "s3:GetObjectVersionAcl",
            "s3:GetObjectVersionTagging",
            "s3:GetObjectVersionTorrent",
            "s3:ListMultipartUploadParts",
            "s3:ListBucket",
            "s3:ListBucketVersions"
        ],
        resources: [assestBucket.arnForObjects("*")]
      })

      assestBucket.grantRead(sourceRole)

      sourceRole.addToPolicy(sourcRolePoliyStatement)
 
      // Asset creation lambda function exec role
      const assetCreateFunctionExecRole = new iam.Role(this, "AssetCreationLambdaFunctionExecRole",{
        assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com')
      });

      assetCreateFunctionExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AWSElementalMediaPackageFullAccess"));

      assetCreateFunctionExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AWSLambdaExecute"));

      const assetFunctionExecPolicyStatement = new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
            "mediapackage-vod:*",
        ],
        resources: ["*"]
      });

      const assetFunctionExecPolicyStatement2 = new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
            "iam:PassRole"
        ],
        resources: [sourceRole.roleArn]
      });
      assetCreateFunctionExecRole.addToPolicy(assetFunctionExecPolicyStatement)
      assetCreateFunctionExecRole.addToPolicy(assetFunctionExecPolicyStatement2)

      // Lambda function invoked by MediaConvert COMPLETE event and create asset
      const assetCreateFunction = new lambda.Function(this, "VOD-AssetCreateFunction", {
        code: lambda.Code.fromAsset("./functions/asset"),
        handler: "app.lambda_handler",
        runtime: lambda.Runtime.PYTHON_3_9,
        role: assetCreateFunctionExecRole,
        environment:{
            "GROUP_ID": packagingGroup.id,
            "SOURCE_ROLE_ARN": sourceRole.roleArn,
            "DISTRIBUTION_DOMAIN": distribution.distributionDomainName,
            "PACKAGE_GROUP_DOMAIN": packagingGroup.attrDomainName
        },
        timeout: Duration.seconds(15)

      });
      // Event rule
      const queueArn = ssm.StringParameter.valueForStringParameter(this ,"/vod/shared/nmediaconvert-queue-arn");

      const mediaConvertRule = new events.Rule(this, "MediaConvertCompleteRule", {
        eventPattern: {
          source: ["aws.mediaconvert"],
          detailType: ["MediaConvert Job State Change"],
          detail: {
            status: ["COMPLETE"],
            queue: [queueArn]
          }
        },
      });

      // asset creation function sfn task
      const assetCreateFunctionTask = new tasks.LambdaInvoke(this, "Asset creation function",{
        lambdaFunction: assetCreateFunction,
        payload: sfn.TaskInput.fromJsonPathAt('$')
      });

      // SNS topic 

      // Notification SNS topic from Shared Resources
      const snsTopicArn = ssm.StringParameter.valueForStringParameter(this, "/vod/shared/notification-topic-arn");

      const snsNotificationTopic = sns.Topic.fromTopicArn(this, "NotificationTopic", snsTopicArn)


      const snsPublishTask = new tasks.SnsPublish(this, "Push Notification", {
        topic: snsNotificationTopic,
        message: sfn.TaskInput.fromJsonPathAt("$.Payload")
      });
      const chain = sfn.Chain.start(assetCreateFunctionTask).next(snsPublishTask);

      const sm = new sfn.StateMachine(this, "assetCreationWorkflow", {
        definition: chain
      });

      // EventBridge trigger sfn statemachine
      mediaConvertRule.addTarget(new targets.SfnStateMachine(sm));

      // asset remover lambda function exec role
      const assestRemoverFunctionRole = new iam.Role(this, "AssestRemoverFunctionRole", {
        assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
      });
      const assetRemoverFunctionExecPolicyStatement = new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
            "mediapackage-vod:*",
        ],
        resources: ["*"]
      });
      assestRemoverFunctionRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AWSElementalMediaPackageFullAccess"))
      
      assestRemoverFunctionRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AWSLambdaExecute"));

      assestRemoverFunctionRole.addToPolicy(assetRemoverFunctionExecPolicyStatement)

      // Lambda function backed custom resource to remove assets in deletion: 
      const assetRemoverFunction = new lambda.Function(this, "VOD-AssetRemoverFunction", {
        code: lambda.Code.fromAsset("./customResource/removeAsset"),
        handler: "custom-resource.on_event",
        runtime: lambda.Runtime.PYTHON_3_9,
        role: assestRemoverFunctionRole,
        timeout: Duration.seconds(15)
      });

      const assetRemoverProvider = new cr.Provider(this, "AssetRemoverProvider", {
        onEventHandler: assetRemoverFunction,
        logRetention: log.RetentionDays.ONE_DAY
      });

      const assetRemoverCustomResource = new CustomResource(this, "AssetRemoverResource", {
        serviceToken: assetRemoverProvider.serviceToken,
        removalPolicy: RemovalPolicy.DESTROY,
        resourceType: "Custom::AssetRemover",
        properties:{
          "PackagingGroupId": packagingGroup.id
        }
      });

      new CfnOutput(this, "BaseURL", {
        value: distribution.domainName,
        description: "Base URL for video on demand"
      });
    }
}