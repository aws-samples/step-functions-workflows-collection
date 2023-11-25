import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { S3ToStepfunctions } from '@aws-solutions-constructs/aws-s3-stepfunctions';
import { Choice, Condition, Fail, JsonPath, Pass, Wait, WaitTime, } from "aws-cdk-lib/aws-stepfunctions";
import { CallAwsService } from "aws-cdk-lib/aws-stepfunctions-tasks";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import { PolicyStatement, Role, ServicePrincipal } from "aws-cdk-lib/aws-iam";


export class TranscriptBedrockWorkflowStack extends cdk.Stack {
	constructor(scope: Construct, id: string, props?: cdk.StackProps) {
		super(scope, id, props);
		// Dest bucket
		const destBucketname = ssm.StringParameter.valueForStringParameter(this, "/vod/shared/dest-bucket-name");
		const destBucket = s3.Bucket.fromBucketName(this, "DestinationBucket", destBucketname);
		destBucket.enableEventBridgeNotification();
		// DDB from shared resources 
		const ddbTableName = ssm.StringParameter.valueForStringParameter(this, '/vod/shared/ddb-table-name');
		const videoTable = dynamodb.Table.fromTableName(this, 'VideoTable', ddbTableName)
		// Transcribe bucket 
		const transcribeBucket = new s3.Bucket(this, "TranscribeBucket")
		// // Create a wait state to pause execution for 10 seconds
		// const bucketKeyName = JsonPath.stringAt("$.detail.object.key");
		const waitFor10Seconds = new Wait(this, 'WaitFor10Seconds', {
			time: WaitTime.duration(cdk.Duration.seconds(10)),
		});

		// LLM modle name: 
		const bedrockParameter = new ssm.StringParameter(this, 'BedrockLLMName', {
			parameterName: '/vod/shared/bedrock-llm-name',
			description: 'Bedrock LLM name',
			stringValue: 'ai21.j2-ultra-v1,'
		});

		// Define a policy statement for S3 access
		const transcriptionPolicy = new PolicyStatement({
			actions: ['s3:*'],
			resources: ['*'],
		});

		// Define a step to check the transcription job status using AWS Transcribe
		const checkTranscriptionStatus = new CallAwsService(this, 'checkTranscriptionStatus', {
			service: 'transcribe',
			comment: "Check transcription job status",
			action: 'getTranscriptionJob',
			parameters: {
				"TranscriptionJobName.$": "$.TranscriptionJob.TranscriptionJob.TranscriptionJobName"
			},
			resultPath: "$.TranscriptionJob",
			additionalIamStatements: [
				transcriptionPolicy,
			],
			iamResources: ['*'],
		});

		// Define a step to start a transcription job using AWS Transcribe
		const startTranscriptionService = new CallAwsService(this, 'startTranscriptionJob', {
			service: 'transcribe',
			comment: "Start transcription job",
			action: 'startTranscriptionJob',
			parameters: {
				Media: {
					MediaFileUri: JsonPath.format('s3://{}/{}', JsonPath.stringAt("$.detail.bucket.name"), JsonPath.stringAt("$.detail.object.key")),
				},
				"IdentifyLanguage": "True",
				"OutputBucketName": transcribeBucket.bucketName,
				"TranscriptionJobName.$": "$$.Execution.Name"
			},
			iamResources: ['*'],
			resultPath: "$.TranscriptionJob",
			additionalIamStatements: [
				transcriptionPolicy,
			],
		});

		// // Define a Pass state to indicate successful completion of the transcription job
		// const pass = new Pass(this, 'Pass', {
		// 	comment: "Transcription job successfully completed",
		// });

		// Define a Fail state to handle cases where the transcription job fails
		const failed = new Fail(this, 'Failed', {
			comment: "Transcription job failed",
		})

		// Define a Lambda layer for Boto3 with Bedrock support
		const layer = new lambda.LayerVersion(this, 'HelperLayer', {
			code: lambda.Code.fromAsset('./resources/layers/bedrock-layer'),
			description: 'Boto3 with bedrock support',
			compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
			removalPolicy: cdk.RemovalPolicy.DESTROY
		});

		// Define a Lambda function for processing the transcription with Bedrock
		const TranscriptToBedrockLambda = new lambda.Function(this, 'TranscriptToBedrockLambda', {
			runtime: lambda.Runtime.PYTHON_3_11,
			code: lambda.Code.fromAsset('./functions/transcriptToBedRock'),
			handler: 'app.lambda_handler',
			timeout: cdk.Duration.seconds(50),
			environment: {
				TABLE_NAME: ddbTableName
			},
			layers: [layer]
		});

		videoTable.grantWriteData(TranscriptToBedrockLambda);

		transcribeBucket.grantRead(TranscriptToBedrockLambda);
		bedrockParameter.grantRead(TranscriptToBedrockLambda);
		// Attach inline policies to the Lambda function role for Bedrock and S3 access
		TranscriptToBedrockLambda.role?.attachInlinePolicy(new iam.Policy(this, 'vod-bedrock-policy', {
			statements: [new iam.PolicyStatement({
				actions: ['bedrock:InvokeModel', 'bedrock:ListFoundationModels'],
				resources: ["arn:aws:bedrock:*::foundation-model/*", "*"],
			})],
		}));

		// Attach inline policies to the Lambda function role for Bedrock and S3 access
		TranscriptToBedrockLambda.role?.attachInlinePolicy(new iam.Policy(this, 's3-policy', {
			statements: [new iam.PolicyStatement({
				actions: ['s3:GetObject'],
				resources: [transcribeBucket.bucketArn],
			})],
		}));

		// Define a Step Functions task to invoke the Bedrock Lambda function
		const invokeBedrockLambda = new tasks.LambdaInvoke(this, "bedrock-task", {
			lambdaFunction: TranscriptToBedrockLambda,
			resultPath: "$.TranscriptionJob"
		})

		// Define a Choice state to determine the next step based on transcription job status
		const checkTranscriptionStatusChoice = new Choice(this, 'CheckTranscriptionStatusChoice', {
			comment: "Check transcription job status",
		});
		checkTranscriptionStatusChoice.when(Condition.stringEquals('$.TranscriptionJob.TranscriptionJob.TranscriptionJobStatus', 'COMPLETED'), invokeBedrockLambda);
		checkTranscriptionStatusChoice.when(Condition.stringEquals('$.TranscriptionJob.TranscriptionJob.TranscriptionJobStatus', 'FAILED'), failed);
		checkTranscriptionStatusChoice.otherwise(waitFor10Seconds);

		// Define a role for the Step Functions state machine
		const stepFunctionRole = new Role(this, 'StepFunctionRole', {
			assumedBy: new ServicePrincipal('states.amazonaws.com'),
		});

		// Add a policy statement to the role for starting transcription jobs
		stepFunctionRole.addToPolicy(new PolicyStatement({
			actions: ['transcribe:StartTranscriptionJob'],
			resources: ['*'],
		}));

		// Define the statemachine chain
		const chain = sfn.Chain
			.start(startTranscriptionService)
			.next(waitFor10Seconds)
			.next(checkTranscriptionStatus)
			.next(checkTranscriptionStatusChoice)

		// Create an instance of the S3ToStepfunctions construct
		new S3ToStepfunctions(this, `transcription-bedrock-statemachine`, {
			stateMachineProps: {
				stateMachineName: `transcription-bedrock-statemachine`,
				definitionBody: sfn.DefinitionBody.fromChainable(chain),
				role: stepFunctionRole,
			},
			eventRuleProps: {
				ruleName: `transcription-bedrock-statemachine-event-rule`,
				eventPattern: {
					detailType: ["Object Created"],
					source: ['aws.s3'],
					detail: {
						bucket: {
							name: [destBucketname]
						},
						object: {
							key: [
								{
									suffix: '.mp4'
								}
							]
						}
					},
				},
			},
		});
	}
}
