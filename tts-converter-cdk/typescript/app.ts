import {
  App,
  CfnOutput,
  Duration,
  RemovalPolicy,
  Stack,
  aws_events as events,
  aws_events_targets as targets,
  aws_iam as iam,
  aws_s3 as s3,
  aws_stepfunctions as sfn,
  aws_stepfunctions_tasks as tasks,
} from "aws-cdk-lib";

import { Polly, S3 } from "aws-sdk";
import { Construct } from "constructs";

export class ttsConverterStack extends Stack {
  constructor(scope: Construct, id: string) {
    super(scope, id);

    // Create Amazon S3 bucket to store TTS text media
    const ttsMediaBucket = new s3.Bucket(this, "ttsMediaBucket", {
      eventBridgeEnabled: true,
      encryption: s3.BucketEncryption.KMS_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY, // note this parameter deletes the bucket upon stack removal
      autoDeleteObjects: true, // note that this parameter deletes bucket content upon stack removal using an AWS Lambda function
    });

    // Create Amazon S3 bucket to store TTS mp3 results
    const ttsResultsBucket = new s3.Bucket(this, "ttsResultsBucket", {
      encryption: s3.BucketEncryption.KMS_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY, // note this parameter deletes the bucket upon stack removal
      autoDeleteObjects: true, // note that this parameter deletes bucket content upon stack removal using an AWS Lambda function
    });

    // AWS Step Function Definition

    // Step to retrieve the text within the object uploaded to Amazon S3
    const getTextFile = new tasks.CallAwsService(this, "GetTextFile", {
      service: "s3",
      action: "getObject",
      parameters: <S3.GetObjectRequest>{
        Bucket: sfn.JsonPath.stringAt("$.detail.bucket.name"),
        Key: sfn.JsonPath.stringAt("$.detail.object.key"),
      },
      resultSelector: {
        filecontent: sfn.JsonPath.stringAt("$.Body"),
      },
      iamResources: [ttsMediaBucket.arnForObjects("*")],
    });

    // Step to call Amazon Polly to synthesis the text to an audio file
    const startSpeechSynthesisTask = new tasks.CallAwsService(
      this,
      "StartSpeechSynthesisTask",
      {
        service: "polly",
        action: "startSpeechSynthesisTask",
        parameters: <Polly.StartSpeechSynthesisTaskInput>{
          OutputFormat: "mp3",
          OutputS3BucketName: ttsResultsBucket.bucketName,
          Text: sfn.JsonPath.stringAt("$.filecontent"),
          TextType: "text",
          OutputS3KeyPrefix: "audio",
          VoiceId: "Amy",
        },
        iamResources: ["*"],
        additionalIamStatements: [
          new iam.PolicyStatement({
            actions: ["s3:putObject"],
            resources: [`${ttsResultsBucket.bucketArn}/*`],
          }),
        ],
      }
    );

    // Wait step while we wait for processing
    const wait = new sfn.Wait(this, "Wait", {
      time: sfn.WaitTime.duration(Duration.seconds(10)),
    });

    // Step to retrieve the Amazon Polly SpeechSynthesisTask object based on its TaskID
    const getSpeechSynthesisTask = new tasks.CallAwsService(
      this,
      "GetSpeechSynthesisTask",
      {
        service: "polly",
        action: "getSpeechSynthesisTask",
        parameters: <Polly.GetSpeechSynthesisTaskInput>{
          TaskId: sfn.JsonPath.stringAt("$.SynthesisTask.TaskId"),
        },
        iamResources: ["*"],
      }
    );

    // Choice step depending on task status
    const speechSynthesisTaskStatus = new sfn.Choice(
      this,
      "SpeechSynthesisTaskStatus"
    );
    const taskComplete = sfn.Condition.stringEquals(
      "$.SynthesisTask.TaskStatus",
      "completed"
    );
    const taskFailed = sfn.Condition.stringEquals(
      "$.SynthesisTask.TaskStatus",
      "failed"
    );

    // Success step on task completion
    const success = new sfn.Succeed(this, "Success");

    // Fail step on task failure
    const failed = new sfn.Fail(this, "Failed", {
      cause: "transcription job failed",
      error: "FAILED",
    });

    // Create AWS Step Function state machine
    const ttsConverterStateMachine = new sfn.StateMachine(
      this,
      "TtsConverter",
      {
        stateMachineName: "tts-converter-typescript",
        definition: sfn.Chain.start(
          getTextFile.next(
            startSpeechSynthesisTask.next(
              wait.next(
                getSpeechSynthesisTask.next(
                  speechSynthesisTaskStatus
                    .when(taskComplete, success)
                    .when(taskFailed, failed)
                    .otherwise(wait)
                )
              )
            )
          )
        ),
        timeout: Duration.minutes(15),
        tracingEnabled: true,
      }
    );

    // Creates an Amazon EventBridge rule that looks for new objects created on the TTS Media Bucket
    const s3MediaTrigger = new events.Rule(this, "S3MediaTrigger", {
      eventPattern: {
        source: ["aws.s3"],
        detailType: ["Object Created"],
        detail: {
          bucket: {
            name: [ttsMediaBucket.bucketName],
          },
        },
      },
      targets: [new targets.SfnStateMachine(ttsConverterStateMachine)],
    });

    // Outputs to assist with testing
    new CfnOutput(this, "TtsMediaBucketOutput", {
      description: "Upload your text files to this bucket",
      value: ttsMediaBucket.bucketName,
    });
    new CfnOutput(this, "TtsResultsBucketOutput", {
      description: "Audio files are created in this bucket",
      value: ttsResultsBucket.bucketName,
    });
  }
}

const app = new App();
new ttsConverterStack(app, "TtsConverterTypescript");
app.synth();
