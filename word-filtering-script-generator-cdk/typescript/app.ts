import {
  App,
  CfnOutput,
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
  aws_events as events,
  aws_events_targets as targets,
  aws_iam as iam,
  aws_s3 as s3,
  aws_stepfunctions as sfn,
  aws_stepfunctions_tasks as tasks,
} from "aws-cdk-lib";

import { S3, TranscribeService } from "aws-sdk";
import { Construct } from "constructs";

interface wordFilteringScriptGeneratorStackProps extends StackProps {
  wordsToFilter: string[];
}

export class wordFilteringScriptGeneratorStack extends Stack {
  constructor(
    scope: Construct,
    id: string,
    props: wordFilteringScriptGeneratorStackProps
  ) {
    super(scope, id, props);

    // Create Amazon S3 bucket to store Transcript media
    const transcriptMediaBucket = new s3.Bucket(this, "TranscriptMediaBucket", {
      eventBridgeEnabled: true,
      encryption: s3.BucketEncryption.KMS_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY, // note this parameter deletes the bucket upon stack removal
      autoDeleteObjects: true, // note that this parameter deletes bucket content upon stack removal using an AWS Lambda function
    });

    // Create Amazon S3 bucket to store transcription results
    const transcriptResultsBucket = new s3.Bucket(
      this,
      "TranscriptResultsBucket",
      {
        encryption: s3.BucketEncryption.KMS_MANAGED,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        enforceSSL: true,
        removalPolicy: RemovalPolicy.DESTROY, // note this parameter deletes the bucket upon stack removal
        autoDeleteObjects: true, // note that this parameter deletes bucket content upon stack removal using an AWS Lambda function
      }
    );

    // AWS Step Function Definition

    // Step to list Vocabulary Filters with the name "wordFilter
    const listVocabularyFilters = new tasks.CallAwsService(
      this,
      "List Vocabulary Filters",
      {
        service: "transcribe",
        action: "listVocabularyFilters",
        parameters: <TranscribeService.ListVocabularyFiltersRequest>{
          NameContains: "wordFilter",
        },
        resultPath: "$.VocabularyListResult",
        iamResources: ["*"],
      }
    );

    // Choice step which checks if the "wordFilter" vocabulary filter exists
    const choiceVocabularyFilter = new sfn.Choice(
      this,
      "Does Vocabulary Filter already exist?"
    );
    const vocabularyFilterExists = sfn.Condition.and(
      sfn.Condition.isPresent("$.VocabularyListResult.VocabularyFilters[0]"),
      sfn.Condition.stringEquals(
        "$.VocabularyListResult.VocabularyFilters[0].VocabularyFilterName",
        "wordFilter"
      )
    );

    // Task step which calls Transcribe to create a new Vocabulary Filter
    const createVocabularyFilter = new tasks.CallAwsService(
      this,
      "Create Vocabulary Filter",
      {
        service: "transcribe",
        action: "createVocabularyFilter",
        parameters: <TranscribeService.CreateVocabularyFilterRequest>{
          LanguageCode: "en-US",
          VocabularyFilterName: "wordFilter",
          Words: props.wordsToFilter,
        },
        resultPath: sfn.JsonPath.DISCARD,
        iamResources: ["*"],
      }
    );

    // Wait steps
    const waitForFilterCreation = new sfn.Wait(
      this,
      "Wait while filter is being created",
      {
        time: sfn.WaitTime.duration(Duration.seconds(20)),
      }
    );
    const waitForTranscriptionJobCompletion = new sfn.Wait(
      this,
      "Wait for Transcription job to complete",
      {
        time: sfn.WaitTime.duration(Duration.seconds(10)),
      }
    );

    // Step to create a transcription job on media file uploaded to Amazon S3
    const startTranscriptionJob = new tasks.CallAwsService(
      this,
      "Start Transcription Job",
      {
        service: "transcribe",
        action: "startTranscriptionJob",
        parameters: <TranscribeService.StartTranscriptionJobRequest>{
          TranscriptionJobName: sfn.JsonPath.stringAt("$$.Execution.Name"),
          Media: {
            MediaFileUri: sfn.JsonPath.format(
              "s3://{}/{}",
              sfn.JsonPath.stringAt("$.detail.bucket.name"),
              sfn.JsonPath.stringAt("$.detail.object.key")
            ),
          },
          LanguageCode: "en-US",
          Settings: {
            VocabularyFilterName: "wordFilter",
            VocabularyFilterMethod: "mask",
          },
          OutputBucketName: transcriptResultsBucket.bucketName,
          OutputKey: sfn.JsonPath.format(
            "{}-temp.json",
            sfn.JsonPath.stringAt("$.detail.object.key")
          ),
        },
        resultPath: "$.TranscriptionResult",
        iamResources: ["*"],
        additionalIamStatements: [
          new iam.PolicyStatement({
            actions: ["s3:getObject"],
            resources: [`${transcriptMediaBucket.bucketArn}/*`],
          }),
        ],
      }
    );

    // Step to get current transcription job status
    const getTranscriptionJobStatus = new tasks.CallAwsService(
      this,
      "Get Transcription Job Status",
      {
        service: "transcribe",
        action: "getTranscriptionJob",
        parameters: <TranscribeService.GetTranscriptionJobRequest>{
          TranscriptionJobName: sfn.JsonPath.stringAt(
            "$.TranscriptionResult.TranscriptionJob.TranscriptionJobName"
          ),
        },
        resultPath: "$.TranscriptionResult",
        iamResources: ["*"],
      }
    );

    // Choice step depending on transcription job status
    const transcriptionJobStatus = new sfn.Choice(
      this,
      "Evaluate Transcription Job Status"
    );
    const jobComplete = sfn.Condition.stringEquals(
      "$.TranscriptionResult.TranscriptionJob.TranscriptionJobStatus",
      "COMPLETED"
    );
    const jobFailed = sfn.Condition.stringEquals(
      "$.TranscriptionResult.TranscriptionJob.TranscriptionJobStatus",
      "FAILED"
    );

    // Step which retrieves the raw transcription output temp object from S3 and outputs just the transcript text
    const getRawTranscriptionResult = new tasks.CallAwsService(
      this,
      "Get Transcript from Raw Transcription Result",
      {
        service: "s3",
        action: "getObject",
        parameters: <S3.GetObjectRequest>{
          Bucket: transcriptResultsBucket.bucketName,
          Key: sfn.JsonPath.format(
            "{}-temp.json",
            sfn.JsonPath.stringAt("$.detail.object.key")
          ),
        },
        resultPath: "$.transcription",
        resultSelector: {
          filecontent: sfn.JsonPath.stringToJson(
            sfn.JsonPath.stringAt("$.Body")
          ),
        },
        iamResources: [transcriptResultsBucket.arnForObjects("*")],
      }
    );

    // Step which stores the transcript text onto S3
    const storeTranscript = new tasks.CallAwsService(
      this,
      "Store Transcript in S3",
      {
        service: "s3",
        action: "putObject",
        parameters: <S3.PutObjectRequest>{
          Bucket: transcriptResultsBucket.bucketName,
          Key: sfn.JsonPath.format(
            "{}-transcript.txt",
            sfn.JsonPath.stringAt("$.detail.object.key")
          ),
          Body: sfn.JsonPath.stringAt(
            "$.transcription.filecontent.results.transcripts[0].transcript"
          ),
        },
        iamResources: [transcriptResultsBucket.arnForObjects("*")],
      }
    );

    // Fail tep on task failure
    const failed = new sfn.Fail(this, "Failed", {
      cause: "Transcription job failed",
      error: "FAILED",
    });

    // Create AWS Step Function state machine
    const wordFilteringScriptGeneratorStateMachine = new sfn.StateMachine(
      this,
      "WordFilteringScriptGenerator",
      {
        stateMachineName: "word-filtering-script-generator-typescript",
        definition: sfn.Chain.start(
          listVocabularyFilters.next(
            choiceVocabularyFilter
              .when(vocabularyFilterExists, startTranscriptionJob)
              .otherwise(
                createVocabularyFilter.next(
                  waitForFilterCreation.next(
                    startTranscriptionJob.next(
                      waitForTranscriptionJobCompletion.next(
                        getTranscriptionJobStatus.next(
                          transcriptionJobStatus
                            .when(
                              jobComplete,
                              getRawTranscriptionResult.next(storeTranscript)
                            )
                            .when(jobFailed, failed)
                            .otherwise(waitForTranscriptionJobCompletion)
                        )
                      )
                    )
                  )
                )
              )
          )
        ),
        timeout: Duration.minutes(15),
        tracingEnabled: true,
      }
    );

    // Creates an Amazon EventBridge rule that looks for new objects created on the Transcription Media Bucket
    const s3MediaTrigger = new events.Rule(this, "S3MediaTrigger", {
      eventPattern: {
        source: ["aws.s3"],
        detailType: ["Object Created"],
        detail: {
          bucket: {
            name: [transcriptMediaBucket.bucketName],
          },
        },
      },
    });
    s3MediaTrigger.addTarget(
      new targets.SfnStateMachine(wordFilteringScriptGeneratorStateMachine)
    );

    // Outputs to assist with testing
    new CfnOutput(this, "TranscriptMediaBucketOutput", {
      description: "Upload your media files to this bucket",
      value: transcriptMediaBucket.bucketName,
    });
    new CfnOutput(this, "TranscriptResultsBucketOutput", {
      description: "Transcripts are created in this bucket",
      value: transcriptResultsBucket.bucketName,
    });
  }
}

const app = new App();
new wordFilteringScriptGeneratorStack(
  app,
  "WordFilteringScriptGeneratorTypescript",
  {
    wordsToFilter: ["amazon"],
  }
);
app.synth();
