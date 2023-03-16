import {
  App,
  Stack,
  StackProps,
  aws_events as events,
  aws_events_targets as targets,
  aws_kms as kms,
  aws_sns as sns,
  aws_sns_subscriptions as subscriptions,
  aws_stepfunctions as sfn,
  aws_stepfunctions_tasks as tasks,
} from "aws-cdk-lib";

import { Construct } from "constructs";

interface sagemakerPipelineNotificationsStackProps extends StackProps {
  notificationEmail: string;
}

export class sagemakerPipelineNotificationsStack extends Stack {
  constructor(
    scope: Construct,
    id: string,
    props: sagemakerPipelineNotificationsStackProps
  ) {
    super(scope, id, props);

    // Create SNS Topic for notifications of failed SageMaker Pipeline executions
    const snsKey = kms.Alias.fromAliasName(this, "SnsKey", "alias/aws/sns");
    const sagemakerPipelineNotificationsTopic = new sns.Topic(
      this,
      "SageMakerPipelineFailedNotification",
      {
        masterKey: snsKey,
      }
    );
    // Subscribe to notifications
    sagemakerPipelineNotificationsTopic.addSubscription(
      new subscriptions.EmailSubscription(props.notificationEmail)
    );

    // AWS Step Function Definition

    // Step to notify of a failed SageMaker Pipeline execution via SNS Topic.
    const notifyFailedSageMakerPipelineExecution = new tasks.SnsPublish(
      this,
      "Notify that a SageMaker Pipeline execution has failed",
      {
        topic: sagemakerPipelineNotificationsTopic,
        integrationPattern: sfn.IntegrationPattern.REQUEST_RESPONSE,
        subject: sfn.JsonPath.format(
          "Amazon SageMaker Pipeline Failed - Pipeline Name: {}",
          sfn.JsonPath.arrayGetItem(
            sfn.JsonPath.stringSplit(
              sfn.JsonPath.stringAt("$.detail.pipelineArn"),
              "/"
            ),
            1
          )
        ),
        message: sfn.TaskInput.fromText(
          sfn.JsonPath.format(
            "The SageMaker Pipeline, {}, started at {} and failed at {}.",
            sfn.JsonPath.arrayGetItem(
              sfn.JsonPath.stringSplit(
                sfn.JsonPath.stringAt("$.detail.pipelineArn"),
                "/"
              ),
              1
            ),
            sfn.JsonPath.stringAt("$.detail.executionStartTime"),
            sfn.JsonPath.stringAt("$.detail.executionEndTime")
          )
        ),
      }
    );

    const sagemakerPipelineNotificationsStateMachine = new sfn.StateMachine(
      this,
      "SageMakerPipelineNotificationsStateMachine",
      {
        stateMachineName: "sagemaker-pipeline-notifications-typescript",
        definition: sfn.Chain.start(notifyFailedSageMakerPipelineExecution),
      }
    );

    // EventBridge rule that triggers the state machine whenever a SageMaker Pipeline execution fails.
    new events.Rule(this, "SageMakerPipelineExecutionFailedTrigger", {
      eventPattern: {
        source: ["aws.sagemaker"],
        detail: { currentPipelineExecutionStatus: ["Failed"] },
        detailType: [
          "SageMaker Model Building Pipeline Execution Status Change",
        ],
      },
      targets: [
        new targets.SfnStateMachine(sagemakerPipelineNotificationsStateMachine),
      ],
    });
  }
}

const app = new App();

new sagemakerPipelineNotificationsStack(
  app,
  "SageMakerPipelineNotificationsTypescript",
  {
    notificationEmail: "admin@example.com",
  }
);
app.synth();
