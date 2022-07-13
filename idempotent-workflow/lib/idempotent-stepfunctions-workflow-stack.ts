import { Duration, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import { IdempotentWorkflow } from "./idempotent-workflow";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as lambdapy from "@aws-cdk/aws-lambda-python-alpha";
import * as sfnt from "aws-cdk-lib/aws-stepfunctions-tasks";

export class IdempotentStepfunctionsWorkflowStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const injectFailureLambda: lambda.IFunction = new lambdapy.PythonFunction(
      this,
      "IdempotencyWorkflowInjectFailure",
      {
        entry: "lambda/inject-failure/",
        runtime: lambda.Runtime.PYTHON_3_9,
        architecture: lambda.Architecture.X86_64,
        index: "index.py",
        handler: "lambda_handler",
        timeout: Duration.seconds(10),
      }
    );

    const myWorkFlowSteps = new sfn.Pass(this, "Here", {
      parameters: {
        result: "Output of step 1",
      },
      resultPath: "$.results.step1",
    })
      .next(
        new sfn.Pass(this, "Goes", {
          parameters: {
            result: "Output of step 2",
          },
          resultPath: "$.results.step2",
        })
      )
      .next(
        new sfn.Pass(this, "Your", {
          parameters: {
            result: "Output of step 3",
          },
          resultPath: "$.results.step3",
        })
      )
      .next(
        new sfn.Pass(this, "Workflow", {
          parameters: {
            result: "Output of step 4",
          },
          resultPath: "$.results.step4",
        })
      )
      .next(
        new sfnt.LambdaInvoke(this, "(which can fail occasionally)", {
          lambdaFunction: injectFailureLambda,
          payloadResponseOnly: true,
          resultPath: "$.results.randomFailureFunc",
        })
      );

    new IdempotentWorkflow(this, "IdempotentStepfunctionsWorkflow", {
      workflowSteps: myWorkFlowSteps,
    });
  }
}
