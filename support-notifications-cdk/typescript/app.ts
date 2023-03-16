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
import { Support } from "aws-sdk";
import { Construct } from "constructs";

interface supportNotificationsStackProps extends StackProps {
  notificationEmail: string;
}

export class supportNotificationsStack extends Stack {
  constructor(
    scope: Construct,
    id: string,
    props: supportNotificationsStackProps
  ) {
    super(scope, id, props);

    // Create SNS Topic for notifications of new case creation which match the severity level
    const snsKey = kms.Alias.fromAliasName(this, "SnsKey", "alias/aws/sns");
    const supportNotificationsTopic = new sns.Topic(
      this,
      "SupportCasesCreatedNotification",
      {
        masterKey: snsKey,
      }
    );
    // Subscribe to notifications
    supportNotificationsTopic.addSubscription(
      new subscriptions.EmailSubscription(props.notificationEmail)
    );

    // AWS Step Function Definition

    // Step to call AWS Support API to retrieve information about the newly created case
    const getSupportCase = new tasks.CallAwsService(
      this,
      "Get Support Case Details",
      {
        service: "support",
        action: "describeCases",
        parameters: <Support.DescribeCasesRequest>{
          CaseIdList: sfn.JsonPath.array(sfn.JsonPath.entirePayload),
        },
        inputPath: "$.detail.case-id",
        resultPath: "$.CaseDetails",
        iamResources: ["*"],
      }
    );

    /**
     * Choice step depending on whether the case matches either the urgent or critical severity level
     * we want to notify on. This is refers to "Production system down" or "Business-critical system
     * down" in AWS console.
     *
     * https://docs.aws.amazon.com/awssupport/latest/APIReference/API_SeverityLevel.html#API_SeverityLevel_Contents
     *
     */

    const determineSeverity = new sfn.Choice(this, "Determine Severity");
    const matchSeverity = sfn.Condition.or(
      sfn.Condition.stringEquals(
        "$.CaseDetails.Cases[0].SeverityCode",
        "critical"
      ),
      sfn.Condition.stringEquals(
        "$.CaseDetails.Cases[0].SeverityCode",
        "urgent"
      )
    );

    // Step to notify of a new case being created via SNS Topic.
    const notifyNewCaseCreated = new tasks.SnsPublish(
      this,
      "Notify that a new case has been created",
      {
        topic: supportNotificationsTopic,
        integrationPattern: sfn.IntegrationPattern.REQUEST_RESPONSE,
        subject: sfn.JsonPath.format(
          "AWS Support Case Created - Case ID: {} - {}",
          sfn.JsonPath.stringAt("$.CaseDetails.Cases[0].DisplayId"),
          sfn.JsonPath.stringAt("$.CaseDetails.Cases[0].Subject")
        ),
        message: sfn.TaskInput.fromText(
          sfn.JsonPath.format(
            "A new AWS Support case (Case ID: {}) has been opened in account {}, with a {} severity by {}. The subject is {}. You can access this case by logging into AWS account {} and clicking the following link: https://console.aws.amazon.com/support/home#/case/?displayId={}&language=en",
            sfn.JsonPath.stringAt("$.CaseDetails.Cases[0].DisplayId"),
            sfn.JsonPath.stringAt("$.account"),
            sfn.JsonPath.stringAt("$.CaseDetails.Cases[0].SeverityCode"),
            sfn.JsonPath.stringAt("$.CaseDetails.Cases[0].SubmittedBy"),
            sfn.JsonPath.stringAt("$.CaseDetails.Cases[0].Subject"),
            sfn.JsonPath.stringAt("$.account"),
            sfn.JsonPath.stringAt("$.CaseDetails.Cases[0].DisplayId")
          )
        ),
      }
    );

    const finished = new sfn.Succeed(this, "Notification not required");

    const supportNotificationsStateMachine = new sfn.StateMachine(
      this,
      "SupportNotificationsStateMachine",
      {
        stateMachineName: "support-notifications-typescript",
        definition: sfn.Chain.start(
          getSupportCase.next(
            determineSeverity
              .when(matchSeverity, notifyNewCaseCreated)
              .otherwise(finished)
          )
        ),
      }
    );

    // EventBridge rule that triggers the state machine whenver a support case is created.
    new events.Rule(this, "SupportCaseCreatedTrigger", {
      eventPattern: {
        source: ["aws.support"],
        detail: { "event-name": ["CreateCase"] },
      },
      targets: [new targets.SfnStateMachine(supportNotificationsStateMachine)],
    });
  }
}

const app = new App();
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: "us-east-1",
};
new supportNotificationsStack(app, "SupportNotificationsTypescript", {
  notificationEmail: "moderator@example.com",
  env: env,
});
app.synth();
