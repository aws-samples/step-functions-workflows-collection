import {
  Stack,
  StackProps,
  aws_lambda as lambda,
  aws_iam as iam,
  aws_stepfunctions_tasks as tasks,
  aws_stepfunctions as sfn,
  Duration,
  CfnOutput
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class WorkflowWithinAWorkflowCdkStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    //Call back Lambda function execution role
    const lambdaFunctionsExecRole = new iam.Role(this, "LambdaFunctionsExecRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
    });
    const sendTaskSuccessPolicy = new iam.Policy(this, "SendTaskSuccessPolicy", {
      statements: [new iam.PolicyStatement({
        actions: ["states:SendTaskSuccess"],
        resources: ["*"]
      })]
    });

    lambdaFunctionsExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"));
    lambdaFunctionsExecRole.attachInlinePolicy(sendTaskSuccessPolicy);

    //Call back Lambda function 
    const callBackLambda = new lambda.Function(this, "Nesting Pattern Callback", {
      runtime: lambda.Runtime.NODEJS_14_X,
      handler: "callback.lambda_handler",
      code: lambda.Code.fromAsset("./functions/callback"),
      role: lambdaFunctionsExecRole,
      timeout: Duration.seconds(25)
    });

    //Building the nested state machine tasks
    const firstLongRunningJob = new sfn.Wait(this, "First long-running job", {
      time: sfn.WaitTime.duration(Duration.seconds(1))
    });

    const needCallBack = new sfn.Choice(this, "Need callback?");
    const needCallBackCondition = sfn.Condition.booleanEquals("$.NeedCallback", true);

    const callBackLambdaTask = new tasks.LambdaInvoke(this, "Callback", {
      lambdaFunction: callBackLambda,
      payload: sfn.TaskInput.fromObject({
        TaskToken: sfn.JsonPath.stringAt("$$.Execution.Input.TaskToken"),
        Message: "Callback right after the first long-running job is completed"
      })
    });

    const secondLongRunningJob = new sfn.Wait(this, "Second long-running job", {
      time: sfn.WaitTime.duration(Duration.seconds(1))
    });

    const reportCompletion = new sfn.Pass(this, "Report completion", {
      result: sfn.Result.fromString("The whole execution is completed including both long-running jobs")
    });

    const needCallBackChain = sfn.Chain.start(callBackLambdaTask).next(secondLongRunningJob);
    const defaultChain = sfn.Chain.start(secondLongRunningJob).next(reportCompletion);

    const nestedStateMachineChain = sfn.Chain.start(firstLongRunningJob)
      .next(needCallBack.when(needCallBackCondition, needCallBackChain)
        .otherwise(defaultChain));

    //Nested state machine
    const nestedStateMachine = new sfn.StateMachine(this, "NestedStateMachine", {
      definition: nestedStateMachineChain
    });

    //Building the main state machine tasks
    const startNewWorkflowAndContinue = new tasks.StepFunctionsStartExecution(this, "Start new workflow and continue", {
      stateMachine: nestedStateMachine,
      comment: "Start an execution of another Step Functions state machine and continue",
      integrationPattern: sfn.IntegrationPattern.REQUEST_RESPONSE,
      input: sfn.TaskInput.fromObject({
        NeedCallback: false,
        AWS_STEP_FUNCTIONS_STARTED_BY_EXECUTION_ID: sfn.JsonPath.stringAt("$$.Execution.Id")
      })
    });

    const startInParallel = new sfn.Parallel(this, "Start in parallel", {
      comment: "Start two executions of the same state machine in parallel"
    });

    const startNewWorkflowAndWaitForCompletion = new tasks.StepFunctionsStartExecution(this, "Start new workflow and wait for completion", {
      stateMachine: nestedStateMachine,
      comment: "Start an execution and wait for its completion",
      integrationPattern: sfn.IntegrationPattern.RUN_JOB,
      input: sfn.TaskInput.fromObject({
        NeedCallback: false,
        AWS_STEP_FUNCTIONS_STARTED_BY_EXECUTION_ID: sfn.JsonPath.stringAt("$$.Execution.Id")
      }),
      outputPath: sfn.JsonPath.stringAt("$.Output")
    });

    const startNewWorkflowAndWaitForCallBack = new tasks.StepFunctionsStartExecution(this, "Start new workflow and wait for callback", {
      stateMachine: nestedStateMachine,
      comment: "Start an execution and wait for it to call back with a task token",
      integrationPattern: sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
      input: sfn.TaskInput.fromObject({
        NeedCallback: true,
        AWS_STEP_FUNCTIONS_STARTED_BY_EXECUTION_ID: sfn.JsonPath.stringAt("$$.Execution.Id"),
        TaskToken: sfn.JsonPath.stringAt("$$.Task.Token")
      })
    })

    startInParallel.branch(startNewWorkflowAndWaitForCompletion);
    startInParallel.branch(startNewWorkflowAndWaitForCallBack);

    const mainStateMachineChain = sfn.Chain.start(startNewWorkflowAndContinue).next(startInParallel);

    //Main state machine
    const mainStateMachine = new sfn.StateMachine(this, "NestedPatternMainStateMachine", {
      definition: mainStateMachineChain
    });

    //outputs
    const stateMachineArn = new CfnOutput(this, 'stateMachineArn', {
      value: mainStateMachine.stateMachineArn,
    });


  }

}
