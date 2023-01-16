import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Duration } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";

export class RedshiftServerlessUnloadStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const resultBucket = new s3.Bucket(
      this,
      "Redshift Serverless UNLOAD results bucket"
    );

    const generateUUID = new sfn.Pass(this, "Generate UUID", {
      parameters: {
        uuid: sfn.JsonPath.uuid(),
      },
    });

    const executeStatement = new tasks.CallAwsService(
      this,
      "ExecuteStatement",
      {
        service: "redshiftdata",
        action: "executeStatement",
        parameters: {
          WorkgroupName: sfn.JsonPath.stringAt(
            "$$.Execution.Input.redshift_workgroup"
          ),
          Database: sfn.JsonPath.stringAt(
            "$$.Execution.Input.redshift_database"
          ),
          Sql: sfn.JsonPath.stringAt(
            "States.Format('unload (\\'{}\\') to \\'s3://" +
              resultBucket.bucketName +
              "/{}/result_\\' iam_role default manifest', $$.Execution.Input.query_without_unload, $.uuid)"
          ),
        },
        iamResources: ["*"],
        iamAction: "redshift-data:ExecuteStatement",
        resultPath: sfn.JsonPath.stringAt("$.executeStatement"),
      }
    );

    const waitState = new sfn.Wait(this, "Wait", {
      time: sfn.WaitTime.duration(Duration.seconds(5)),
    });

    const describeStatement = new tasks.CallAwsService(
      this,
      "DescribeStatement",
      {
        service: "redshiftdata",
        action: "describeStatement",
        parameters: {
          Id: sfn.JsonPath.stringAt("$.executeStatement.Id"),
        },
        iamResources: ["*"],
        iamAction: "redshift-data:DescribeStatement",
        resultPath: sfn.JsonPath.stringAt("$.describeStatement"),
      }
    );

    const manifestFileNotFound = new sfn.Fail(this, "Manifest file not found", {
      cause: "The manifest file could not be found in the output S3 bucket.",
      error: "Manifest file not found",
    });

    const getManifestFile = new tasks.CallAwsService(
      this,
      "Get manifest file",
      {
        service: "s3",
        action: "getObject",
        parameters: {
          Bucket: resultBucket.bucketName,
          Key: sfn.JsonPath.stringAt(
            "States.Format('{}/result_manifest', $.uuid)"
          ),
        },
        iamResources: [resultBucket.bucketArn + "/*"],
        iamAction: "s3:GetObject",
        resultSelector: {
          result: sfn.JsonPath.stringAt("States.StringToJson($.Body)"),
        },
        resultPath: sfn.JsonPath.stringAt("$.getManifest"),
      }
    ).addCatch(manifestFileNotFound);

    const abortedOrFailed = new sfn.Fail(this, "Query aborted or failed", {
      cause: "The Redshift query terminated with status ABORTED or FAILED.",
      error: "Query aborted or failed",
    });

    const queryStatusChoice = new sfn.Choice(this, "Query finished?")
      .when(
        sfn.Condition.stringEquals("$.describeStatement.Status", "FINISHED"),
        getManifestFile
      )
      .when(
        sfn.Condition.or(
          sfn.Condition.stringMatches("$.describeStatement.Status", "ABORTED"),
          sfn.Condition.stringMatches("$.describeStatement.Status", "FAILED")
        ),
        abortedOrFailed
      )
      .otherwise(waitState);

    const definition = generateUUID
      .next(executeStatement)
      .next(waitState)
      .next(describeStatement)
      .next(queryStatusChoice);

    const workflow = new sfn.StateMachine(this, "StateMachine", {
      definition,
    });

    workflow.addToRolePolicy(
      new iam.PolicyStatement({
        resources: ["*"],
        actions: ["redshift-serverless:GetCredentials"],
      })
    );
  }
}
