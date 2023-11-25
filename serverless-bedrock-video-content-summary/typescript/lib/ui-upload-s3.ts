import {
  Stack,
  StackProps,
  aws_iam as iam,
  aws_s3 as s3,
  aws_s3_deployment as s3deploy,
  aws_sns as sns,
  aws_apigateway as apigateway,
  aws_lambda as lambda,
  // aws_mediaconvert as mediaconvert,
  aws_dynamodb as ddb,
  aws_cloudfront as cloudfront,
  aws_cloudfront_origins as cloudfront_origins,
  Duration,
  CfnOutput,
  RemovalPolicy,
  custom_resources as cr,
  aws_logs as log,
  aws_ssm as ssm,
  aws_logs as logs,
  CustomResource
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class UiS3UploadStack extends Stack {

  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    // import shared resource: SNS, DDB, S3 Buckets
    // SNS topic
    const snsTopicArn = ssm.StringParameter.valueForStringParameter(this, "/vod/shared/notification-topic-arn");
    const snsNotificationTopic = sns.Topic.fromTopicArn(this, "NotificationTopic", snsTopicArn);
    // DDB talbe
    const ddbTableName = ssm.StringParameter.valueForStringParameter(this, '/vod/shared/ddb-table-name');
    const videoTable = ddb.Table.fromTableName(this, 'VideoTable', ddbTableName);
    // Dest bucket
    const destBucketname = ssm.StringParameter.valueForStringParameter(this, "/vod/shared/dest-bucket-name");
    const destBucket = s3.Bucket.fromBucketName(this, "DestinationBucket", destBucketname);
    // Source bucket
    const sourceBucketname = ssm.StringParameter.valueForStringParameter(this, '/vod/shared/source-bucket-name');
    const uploadBucket = s3.Bucket.fromBucketName(this, 'SourceBucket', sourceBucketname);

    // website bucket, holding the static html page
    const websiteBucket = new s3.Bucket(this, 'WebsiteBucket', {
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true
    });

    // deploy the static-content to the website bucket
    new s3deploy.BucketDeployment(this, 'DeployWebsite', {
      sources: [s3deploy.Source.asset('static-content')],
      destinationBucket: websiteBucket,
    });

    // Create CloudFront OAI for CloudFront accessing the S3 bucket static files and s3 bucket policy
    const cloudfrontOAI = new cloudfront.OriginAccessIdentity(this, 'cloudfront-OAI', {});

    websiteBucket.addToResourcePolicy(new iam.PolicyStatement({
      actions: ['s3:GetObject'],
      resources: [websiteBucket.arnForObjects('*')],
      principals: [new iam.CanonicalUserPrincipal(cloudfrontOAI.cloudFrontOriginAccessIdentityS3CanonicalUserId)]
    }));

    // upload function to upload the video to the website bucket
    const uploadFunction = new lambda.Function(this, 'UploadFunction', {
      code: lambda.Code.fromAsset('./functions/uploadVideo'),
      handler: 'app.lambda_handler',
      runtime: lambda.Runtime.PYTHON_3_9,
      environment: {
        SOURCE_BUCKET: sourceBucketname,
        DESTINATION_BUCKET: destBucketname,
        DDB_TABLE_NAME: ddbTableName,
        SNS_TOPIC_ARN: snsTopicArn,
      }
    });
    snsNotificationTopic.grantPublish(uploadFunction)
    videoTable.grantWriteData(uploadFunction);

    // api gateway to expose the upload function
    const api = new apigateway.RestApi(this, 'Endpoint', {
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['*'],
      },
    });

    uploadBucket.grantPut(uploadFunction);
    destBucket.grantPut(uploadFunction)

    // create the CloudFront distribution 
    const distribution = new cloudfront.Distribution(this, 'SiteDistribution', {
      defaultRootObject: 'index.html',
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
      errorResponses: [
        {
          httpStatus: 403,
          responseHttpStatus: 403,
          responsePagePath: '/error.html',
          ttl: Duration.minutes(30),
        }
      ],
      defaultBehavior: {
        origin: new cloudfront_origins.S3Origin(websiteBucket, { originAccessIdentity: cloudfrontOAI }),
        compress: true,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      }
    });

    // custom resource to rewrite the static content to the website bucket
    const staticUploadFunction = new lambda.Function(this, 'UploadStaticContentFunction', {
      code: lambda.Code.fromAsset('./customResource/uploadFunction'),
      handler: 'custom-resource.on_event',
      runtime: lambda.Runtime.PYTHON_3_9,
      environment: {
        WEBSITE_BUCKET: websiteBucket.bucketName,
        API_ENDPOINT: api.url,
        DISTRIBUTION_ID: distribution.distributionId,
      },
      timeout: Duration.seconds(2 * 15)
    });
    distribution.grantCreateInvalidation(staticUploadFunction)

    // custom resource to dynamically change the API endpoint to js file
    const staticUploadProvider = new cr.Provider(this, 'StaticUploadProvider', {
      onEventHandler: staticUploadFunction,
      logRetention: log.RetentionDays.ONE_DAY
    });

    const staticUploadFunctionCustomResource = new CustomResource(this, 'StaticUploadResource', {
      serviceToken: staticUploadProvider.serviceToken,
      removalPolicy: RemovalPolicy.DESTROY,
      resourceType: 'Custom::StaticContentUploader',
    });

    staticUploadFunctionCustomResource.node.addDependency(distribution)
    websiteBucket.grantReadWrite(staticUploadFunction);

    // Lambda function that query the ddb table and send back to frontend
    const queryDescriptionFuntion = new lambda.Function(this, 'QueryDescriptionFunction', {
      code: lambda.Code.fromAsset('functions/queryDescriptions'),
      handler: 'app.lambda_handler',
      runtime: lambda.Runtime.PYTHON_3_10,
      environment: {
        TABLE_NAME: ddbTableName
      }
    });
    videoTable.grantReadData(queryDescriptionFuntion);

    // add lambda proxy to api to get exposed.
    api.root.addMethod('ANY', new apigateway.LambdaIntegration(uploadFunction));
    const videos = api.root.addResource('video');
    const video = videos.addResource('{videoId}');
    video.addMethod('GET', new apigateway.LambdaIntegration(queryDescriptionFuntion));

    // output
    new CfnOutput(this, 'UIEndpoint', { value: distribution.distributionDomainName });

  }
}  