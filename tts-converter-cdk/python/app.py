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


class ttsConverterStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create Amazon S3 bucket to store TTS text media
        tts_media_bucket = s3.Bucket(
            self,
            "TtsMediaBucket",
            event_bridge_enabled=True,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,  # note this parameter deletes the bucket upon stack removal
            auto_delete_objects=True,  # note that this parameter deletes bucket content upon stack removal using an AWS Lambda function
        )

        # Create Amazon S3 bucket to store TTS mp3 results
        tts_results_bucket = s3.Bucket(
            self,
            "TtsResultBucket",
            encryption=s3.BucketEncryption.KMS_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,  # note this parameter deletes the bucket upon stack removal
            auto_delete_objects=True,  # note that this parameter deletes bucket content upon stack removal using an AWS Lambda function
        )

        # AWS Step Function Definition

        # Step to retrieve the text within the object uploaded to Amazon S3
        get_text_file = tasks.CallAwsService(
            self,
            "GetTextFile",
            service="s3",
            action="getObject",
            parameters={
                "Bucket": sfn.JsonPath.string_at("$.detail.bucket.name"),
                "Key": sfn.JsonPath.string_at("$.detail.object.key"),
            },
            result_selector={"filecontent": sfn.JsonPath.string_at("$.Body")},
            iam_resources=[tts_media_bucket.arn_for_objects("*")],
        )

        # Step to call Amazon Polly to synthesis the text to an audio file
        start_speech_synthesis_task = tasks.CallAwsService(
            self,
            "StartSpeechSynthesisTask",
            service="polly",
            action="startSpeechSynthesisTask",
            parameters={
                "OutputFormat": "mp3",
                "OutputS3BucketName": tts_results_bucket.bucket_name,
                "Text": sfn.JsonPath.string_at("$.filecontent"),
                "TextType": "text",
                "OutputS3KeyPrefix": "audio",
                "VoiceId": "Amy",
            },
            iam_resources=["*"],
            additional_iam_statements=[
                iam.PolicyStatement(
                    actions=["s3:putObject"],
                    resources=[f"{tts_results_bucket.bucket_arn}/*"],
                )
            ],
        )

        # Wait step while we wait for processing
        wait = sfn.Wait(self, "Wait", time=sfn.WaitTime.duration(Duration.seconds(10)))

        # Step to retrieve the Amazon Polly SpeechSynthesisTask object based on its TaskID
        get_speech_synthesis_task = tasks.CallAwsService(
            self,
            "GetSpeechSynthesisTask",
            service="polly",
            action="getSpeechSynthesisTask",
            parameters={
                "TaskId": sfn.JsonPath.string_at("$.SynthesisTask.TaskId"),
            },
            iam_resources=["*"],
        )

        # Choice step depending on task status
        speech_synthesis_task_status = sfn.Choice(self, "SpeechSynthesisTaskStatus")
        task_complete = sfn.Condition.string_equals(
            "$.SynthesisTask.TaskStatus", "completed"
        )
        task_failed = sfn.Condition.string_equals(
            "$.SynthesisTask.TaskStatus", "failed"
        )

        # Success step on task completion
        success = sfn.Succeed(self, "Success")

        # Fail step on task failure
        failed = sfn.Fail(
            self,
            "Failed",
            cause="transcription job failed",
            error="FAILED",
        )

        # Create AWS Step Function state machine
        tts_converter_state_machine = sfn.StateMachine(
            self,
            "TtsConverter",
            state_machine_name="tts-converter-python",
            definition=sfn.Chain.start(
                get_text_file.next(
                    start_speech_synthesis_task.next(
                        wait.next(
                            get_speech_synthesis_task.next(
                                speech_synthesis_task_status.when(
                                    task_complete, success
                                )
                                .when(task_failed, failed)
                                .otherwise(wait)
                            )
                        )
                    )
                )
            ),
            timeout=Duration.minutes(15),
            tracing_enabled=True,
        )

        # Creates an Amazon EventBridge rule that looks for new objects created on the TTS Media Bucket
        s3_media_trigger = events.Rule(
            self,
            "S3MediaTrigger",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={"bucket": {"name": [tts_media_bucket.bucket_name]}},
            ),
            targets=[targets.SfnStateMachine(tts_converter_state_machine)],
        )

        # Outputs to assist with testing
        CfnOutput(
            self,
            "TtsMediaBucketOutput",
            description="Upload your text files to this bucket",
            value=tts_media_bucket.bucket_name,
        )
        CfnOutput(
            self,
            "TtsResultsBucketOutput",
            description="Audio files are created in this bucket",
            value=tts_results_bucket.bucket_name,
        )


app = App()
ttsConverterStack(
    app,
    "TtsConverterPython",
)
app.synth()
