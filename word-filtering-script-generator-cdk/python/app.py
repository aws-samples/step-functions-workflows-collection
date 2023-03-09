#!/usr/bin/env python

from aws_cdk import (
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
)

from constructs import Construct


class wordFilteringScriptGeneratorStack(Stack):
    def __init__(
        self, scope: Construct, id: str, words_to_filter: list[str], **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Create Amazon S3 bucket to store Transcript media
        transcript_media_bucket = s3.Bucket(
            self,
            "TranscriptMediaBucket",
            event_bridge_enabled=True,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,  # note this parameter deletes the bucket upon stack removal
            auto_delete_objects=True,  # note that this parameter deletes bucket content upon stack removal using an AWS Lambda function
        )

        # Create Amazon S3 bucket to store transcription results
        transcript_results_bucket = s3.Bucket(
            self,
            "TranscriptResultBucket",
            encryption=s3.BucketEncryption.KMS_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,  # note this parameter deletes the bucket upon stack removal
            auto_delete_objects=True,  # note that this parameter deletes bucket content upon stack removal using an AWS Lambda function
        )

        # AWS Step Function Definition

        # Step to list Vocabulary Filters with the name "wordFilter"
        list_vocabulary_filters = tasks.CallAwsService(
            self,
            "List Vocabulary Filters",
            service="transcribe",
            action="listVocabularyFilters",
            parameters={
                "NameContains": "wordFilter",
            },
            result_path="$.VocabularyListResult",
            iam_resources=["*"],
        )

        # Choice step which checks if the "wordFilter" vocabulary filter exists
        choice_vocabulary_filter = sfn.Choice(
            self, "Does Vocabulary Filter already exist?"
        )
        vocabulary_filter_exists = sfn.Condition.and_(
            sfn.Condition.is_present("$.VocabularyListResult.VocabularyFilters[0]"),
            sfn.Condition.string_equals(
                "$.VocabularyListResult.VocabularyFilters[0].VocabularyFilterName",
                "wordFilter",
            ),
        )

        # Task step which calls Transcribe to create a new Vocabulary Filter
        create_vocabulary_filter = tasks.CallAwsService(
            self,
            "Create Vocabulary Filter",
            service="transcribe",
            action="createVocabularyFilter",
            parameters={
                "LanguageCode": "en-US",
                "VocabularyFilterName": "wordFilter",
                "Words": words_to_filter,
            },
            result_path=sfn.JsonPath.DISCARD,
            iam_resources=["*"],
        )

        # Wait steps
        wait_for_filter_creation = sfn.Wait(
            self,
            "Wait while filter is being created",
            time=sfn.WaitTime.duration(Duration.seconds(20)),
        )
        wait_for_transcription_job_completion = sfn.Wait(
            self,
            "Wait for Transcription job to complete",
            time=sfn.WaitTime.duration(Duration.seconds(10)),
        )

        # Step to create a transcription job on media file uploaded to Amazon S3
        start_transcription_job = tasks.CallAwsService(
            self,
            "Start Transcription Job",
            service="transcribe",
            action="startTranscriptionJob",
            parameters={
                "Media": {
                    "MediaFileUri": sfn.JsonPath.format(
                        "s3://{}/{}",
                        sfn.JsonPath.string_at("$.detail.bucket.name"),
                        sfn.JsonPath.string_at("$.detail.object.key"),
                    )
                },
                "OutputBucketName": transcript_results_bucket.bucket_name,
                "OutputKey": sfn.JsonPath.format(
                    "{}-temp.json", sfn.JsonPath.string_at("$.detail.object.key")
                ),
                "LanguageCode": "en-US",
                "TranscriptionJobName": sfn.JsonPath.string_at("$$.Execution.Name"),
                "Settings": {
                    "VocabularyFilterMethod": "mask",
                    "VocabularyFilterName": "wordFilter",
                },
            },
            result_path="$.TranscriptionResult",
            iam_resources=["*"],
            additional_iam_statements=[
                iam.PolicyStatement(
                    actions=["s3:getObject"],
                    resources=[f"{transcript_media_bucket.bucket_arn}/*"],
                )
            ],
        )

        # Step to get current transcription job status
        get_transcription_job_status = tasks.CallAwsService(
            self,
            "Get Transcription Job Status",
            service="transcribe",
            action="getTranscriptionJob",
            parameters={
                "TranscriptionJobName": sfn.JsonPath.string_at(
                    "$.TranscriptionResult.TranscriptionJob.TranscriptionJobName"
                ),
            },
            result_path="$.TranscriptionResult",
            iam_resources=["*"],
        )

        # Choice step depending on transcription job status
        transcription_job_status = sfn.Choice(
            self,
            "Evaluate Transcription Job Status",
        )
        job_complete = sfn.Condition.string_equals(
            "$.TranscriptionResult.TranscriptionJob.TranscriptionJobStatus", "COMPLETED"
        )
        job_failed = sfn.Condition.string_equals(
            "$.TranscriptionResult.TranscriptionJob.TranscriptionJobStatus", "FAILED"
        )

        # Step which retrieves the raw transcription output temp object from S3 and outputs just the transcript text
        get_raw_transcription_result = tasks.CallAwsService(
            self,
            "Get Transcript from Raw Transcription Result",
            service="s3",
            action="getObject",
            parameters={
                "Bucket": transcript_results_bucket.bucket_name,
                "Key": sfn.JsonPath.format(
                    "{}-temp.json", sfn.JsonPath.string_at("$.detail.object.key")
                ),
            },
            result_path="$.transcription",
            result_selector={
                "filecontent": sfn.JsonPath.string_to_json(
                    sfn.JsonPath.string_at("$.Body")
                ),
            },
            iam_resources=[transcript_results_bucket.arn_for_objects("*")],
        )

        # Step which stores the transcript text onto S3
        store_transcript = tasks.CallAwsService(
            self,
            "Store Transcript in S3",
            service="s3",
            action="putObject",
            parameters={
                "Bucket": transcript_results_bucket.bucket_name,
                "Key": sfn.JsonPath.format(
                    "{}-transcript.txt", sfn.JsonPath.string_at("$.detail.object.key")
                ),
                "Body": sfn.JsonPath.string_at(
                    "$.transcription.filecontent.results.transcripts[0].transcript"
                ),
            },
            iam_resources=[transcript_results_bucket.arn_for_objects("*")],
        )

        # Fail step on task failure
        failed = sfn.Fail(
            self,
            "Failed",
            cause="Transcription job failed",
            error="FAILED",
        )

        # Create AWS Step Function state machine
        word_filtering_script_generator_state_machine = sfn.StateMachine(
            self,
            "WordFilteringScriptGenerator",
            state_machine_name="word-filtering-script-generator-python",
            definition=sfn.Chain.start(
                list_vocabulary_filters.next(
                    choice_vocabulary_filter.when(
                        vocabulary_filter_exists, start_transcription_job
                    ).otherwise(
                        create_vocabulary_filter.next(
                            wait_for_filter_creation.next(
                                start_transcription_job.next(
                                    wait_for_transcription_job_completion.next(
                                        get_transcription_job_status.next(
                                            transcription_job_status.when(
                                                job_complete,
                                                get_raw_transcription_result.next(
                                                    store_transcript
                                                ),
                                            )
                                            .when(job_failed, failed)
                                            .otherwise(
                                                wait_for_transcription_job_completion
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            ),
            timeout=Duration.minutes(15),
            tracing_enabled=True,
        )

        # Creates an Amazon EventBridge rule that looks for new objects created on the Transcription Media Bucket
        s3_media_trigger = events.Rule(
            self,
            "S3MediaTrigger",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={"bucket": {"name": [transcript_media_bucket.bucket_name]}},
            ),
        )
        s3_media_trigger.add_target(
            targets.SfnStateMachine(word_filtering_script_generator_state_machine)
        )

        # Outputs to assist with testing
        CfnOutput(
            self,
            "TranscriptMediaBucketOutput",
            description="Upload your media files to this bucket",
            value=transcript_media_bucket.bucket_name,
        )
        CfnOutput(
            self,
            "TranscriptResultsBucketOutput",
            description="Transcripts are created in this bucket",
            value=transcript_results_bucket.bucket_name,
        )


app = App()
wordFilteringScriptGeneratorStack(
    app,
    "WordFilteringScriptGeneratorPython",
    words_to_filter=["amazon"],
)
app.synth()
