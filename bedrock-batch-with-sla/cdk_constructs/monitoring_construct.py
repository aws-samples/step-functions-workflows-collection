import aws_cdk as cdk
import aws_cdk.aws_sns as sns
import aws_cdk.aws_sns_subscriptions as sns_subscriptions
import aws_cdk.aws_cloudwatch as cloudwatch
import aws_cdk.aws_cloudwatch_actions as cloudwatch_actions
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as events_targets
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_notifications as s3_notifications
import aws_cdk.aws_lambda as lambda_
from constructs import Construct
import math


class MonitoringConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        model_id: str,
        stuck_threshold_minutes: int,
        input_bucket: s3.Bucket,
        resume_fn: lambda_.Function,
        trigger_fn: lambda_.Function,
        registrar_fn: lambda_.Function,
    ) -> None:
        super().__init__(scope, construct_id)

        self.alarm_topic = sns.Topic(
            self, "AlarmTopic",
            topic_name="bedrock-batch-sla-alarms",
            display_name="Bedrock Batch SLA Alarms",
        )

        self.alarm_topic.add_subscription(sns_subscriptions.LambdaSubscription(trigger_fn))

        evaluation_periods = math.ceil(stuck_threshold_minutes / 5)

        self.stuck_job_alarm = cloudwatch.Alarm(
            self, "StuckJobAlarm",
            alarm_name="bedrock-batch-sla-stuck-job",
            alarm_description="Detects when a Bedrock batch job is stuck",
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            threshold=0,
            evaluation_periods=evaluation_periods,
            datapoints_to_alarm=evaluation_periods,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            metric=cloudwatch.MathExpression(
                expression="IF(pending > 0 AND tokens == 0, 1, 0)",
                using_metrics={
                    "pending": cloudwatch.Metric(
                        namespace="AWS/Bedrock/Batch",
                        metric_name="NumberOfRecordsPendingProcessing",
                        dimensions_map={"ModelId": model_id},
                        statistic="Average",
                        period=cdk.Duration.minutes(5),
                    ),
                    "tokens": cloudwatch.Metric(
                        namespace="AWS/Bedrock/Batch",
                        metric_name="NumberOfInputTokensProcessedPerMinute",
                        dimensions_map={"ModelId": model_id},
                        statistic="Average",
                        period=cdk.Duration.minutes(5),
                    ),
                },
            ),
        )

        self.stuck_job_alarm.add_alarm_action(cloudwatch_actions.SnsAction(self.alarm_topic))

        self.batch_job_rule = events.Rule(
            self, "BatchJobStateChangeRule",
            rule_name="bedrock-batch-sla-job-state-change",
            description="Capture Bedrock batch job terminal state changes",
            event_pattern=events.EventPattern(
                source=["aws.bedrock"],
                detail_type=["Batch Inference Job State Change"],
                detail={"status": ["Completed", "Failed", "Expired", "PartiallyCompleted"]},
            ),
        )

        self.batch_job_rule.add_target(events_targets.LambdaFunction(resume_fn))

        input_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notifications.LambdaDestination(registrar_fn),
            s3.NotificationKeyFilter(suffix=".jsonl"),
        )
