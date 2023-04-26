import { Construct } from 'constructs';
import {
  Aws,
  Stack,
  StackProps,
  aws_lambda as lambda,
  aws_iam as iam,
  aws_sqs as sqs,
  aws_logs as logs,
  aws_stepfunctions_tasks as tasks,
  aws_stepfunctions as sfn,
  Duration,
  CfnOutput
} from 'aws-cdk-lib';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
export class ProcesshighvolumemessagesSqsExpressStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    //Basic Lambda function execution role
    const lambdaFunctionsExecRole = new iam.Role(this, "LambdaFunctionsExecRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
    });
    lambdaFunctionsExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"));

    //Base 64 decode Lambda function
    const base64Decode = new lambda.Function(this, "Base 64 Decode", {
      runtime: lambda.Runtime.PYTHON_3_7,
      handler: "base64-decode.lambda_handler",
      code: lambda.Code.fromAsset("./functions/base64-decode"),
      role: lambdaFunctionsExecRole,
      timeout: Duration.seconds(20)
    });

    //Generate statistics Lambda functions
    const generateStatistics = new lambda.Function(this, "Generate Statistics", {
      runtime: lambda.Runtime.PYTHON_3_7,
      handler: "generate-statistics.lambda_handler",
      code: lambda.Code.fromAsset("./functions/generate-statistics"),
      role: lambdaFunctionsExecRole,
      timeout: Duration.seconds(20)
    });

    //String cleaner Lambda function
    const stringCleaner = new lambda.Function(this, "String Cleaner", {
      runtime: lambda.Runtime.PYTHON_3_7,
      handler: "string-cleaner.lambda_handler",
      code: lambda.Code.fromAsset("./functions/string-cleaner"),
      role: lambdaFunctionsExecRole,
      timeout: Duration.seconds(20)
    });

    //Tokenizer counter Lambda function
    const tokenizerCounter = new lambda.Function(this, "Tokenize and Count", {
      runtime: lambda.Runtime.PYTHON_3_7,
      handler: "tokenizer-counter.lambda_handler",
      code: lambda.Code.fromAsset("./functions/tokenizer-counter"),
      role: lambdaFunctionsExecRole,
      timeout: Duration.seconds(20)
    });

    //Building state machine tasks 
    const base64DecodeLambdaTask = new tasks.LambdaInvoke(this, "Decode base64 string", {
      lambdaFunction: base64Decode,
      payload: sfn.TaskInput.fromJsonPathAt("$"),
      outputPath: sfn.JsonPath.stringAt("$.Payload")
    });

    const generateStatisticsLambdaTask = new tasks.LambdaInvoke(this, "Generate statistics", {
      lambdaFunction: generateStatistics,
      payload: sfn.TaskInput.fromJsonPathAt("$"),
      outputPath: sfn.JsonPath.stringAt("$.Payload")
    });

    const stringCleanerLambdaTask = new tasks.LambdaInvoke(this, "Remove special characters", {
      lambdaFunction: stringCleaner,
      payload: sfn.TaskInput.fromJsonPathAt("$"),
      outputPath: sfn.JsonPath.stringAt("$.Payload")
    });

    const tokenizerCounterLambdaTask = new tasks.LambdaInvoke(this, "Tokenize and count", {
      lambdaFunction: tokenizerCounter,
      payload: sfn.TaskInput.fromJsonPathAt("$"),
      outputPath: sfn.JsonPath.stringAt("$.Payload")
    });

    const stateMachineChain = sfn.Chain
      .start(base64DecodeLambdaTask)
      .next(generateStatisticsLambdaTask)
      .next(stringCleanerLambdaTask)
      .next(tokenizerCounterLambdaTask);



    //Log group for express state machine
    const expressLogGroup = new logs.LogGroup(this, "ExpressLogGroup");

    //Express state machine
    const stateMachine = new sfn.StateMachine(this, "ExpressStateMachineForTextProcessing", {
      definition: stateMachineChain,
      stateMachineType: sfn.StateMachineType.EXPRESS,
      logs: {
        destination: expressLogGroup,
        level: sfn.LogLevel.ALL,
        includeExecutionData: true
      }
    });

    //Execution role for trigger on SQS Lambda function
    const sqsLambdaFunctionExecRole = new iam.Role(this, "sqsLambdaFunctionExecRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
    });
    const lambdaStartStateMachinePolicy = new iam.Policy(this, "LambdaStateMachinePermissions", {
      statements: [new iam.PolicyStatement({
        actions: ["states:StartExecution"],
        resources: [stateMachine.stateMachineArn]
      })]
    });

    sqsLambdaFunctionExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaSQSQueueExecutionRole"));
    sqsLambdaFunctionExecRole.attachInlinePolicy(lambdaStartStateMachinePolicy);

    //Trigger on SQS Lambda function, this Lambda function will trigger the state machine when messages arrive in the SQS queue
    const sqsLambda = new lambda.Function(this, "Nesting Pattern Callback", {
      runtime: lambda.Runtime.PYTHON_3_7,
      handler: "trigger-on-sqs.lambda_handler",
      code: lambda.Code.fromAsset("./functions/trigger-on-sqs"),
      environment: {
        "STATE_MACHINE_ARN": stateMachine.stateMachineArn
      },
      role: sqsLambdaFunctionExecRole,
      timeout: Duration.seconds(30)
    });

    //SQS queue
    const sqsQueue = new sqs.Queue(this, "Queue", {
      encryption: sqs.QueueEncryption.SQS_MANAGED
    });

    //Event source mapping for trigger on SQS Lambda function
    const eventSource = new SqsEventSource(sqsQueue, {
      batchSize: 1
    });

    sqsLambda.addEventSource(eventSource);

    //Outputs
    const sqsResource = new CfnOutput(this, "SQSResource", {
      value: sqsQueue.queueArn
    });

    const sqsSampleMessage = new CfnOutput(this, "SQSSampleMessage", {
      description: "Sample input to SQS Queue",
      value: `{ 
        "input": "QW5kIGxpa2UgdGhlIGJhc2VsZXNzIGZhYnJpYyBvZiB0aGlzIHZpc2lvbiwgVGhlIGNsb3VkLWNhcHBlZCB0b3dlcnMsIHRoZSBnb3JnZW91cyBwYWxhY2VzLCBUaGUgc29sZW1uIHRlbXBsZXMsIHRoZSBncmVhdCBnbG9iZSBpdHNlbGbigJQgWWVhLCBhbGwgd2hpY2ggaXQgaW5oZXJpdOKAlHNoYWxsIGRpc3NvbHZlLCBBbmQgbGlrZSB0aGlzIGluc3Vic3RhbnRpYWwgcGFnZWFudCBmYWRlZCwgTGVhdmUgbm90IGEgcmFjayBiZWhpbmQuIFdlIGFyZSBzdWNoIHN0dWZmIEFzIGRyZWFtcyBhcmUgbWFkZSBvbiwgYW5kIG91ciBsaXR0bGUgbGlmZSBJcyByb3VuZGVkIHdpdGggYSBzbGVlcC4gU2lyLCBJIGFtIHZleGVkLiBCZWFyIHdpdGggbXkgd2Vha25lc3MuIE15IG9sZCBicmFpbiBpcyB0cm91YmxlZC4gQmUgbm90IGRpc3R1cmJlZCB3aXRoIG15IGluZmlybWl0eS4gSWYgeW91IGJlIHBsZWFzZWQsIHJldGlyZSBpbnRvIG15IGNlbGwgQW5kIHRoZXJlIHJlcG9zZS4gQSB0dXJuIG9yIHR3byBJ4oCZbGwgd2FsayBUbyBzdGlsbCBteSBiZWF0aW5nIG1pbmQu"
      }`
    });

    const stateMachineArn = new CfnOutput(this, "StateMachineArn", {
      value: stateMachine.stateMachineArn,
    });

    const executionInput = new CfnOutput(this, "ExecutionInput", {
      description: "Sample input to StartExecution",
      value: `{ 
        "input": "QW5kIGxpa2UgdGhlIGJhc2VsZXNzIGZhYnJpYyBvZiB0aGlzIHZpc2lvbiwgVGhlIGNsb3VkLWNhcHBlZCB0b3dlcnMsIHRoZSBnb3JnZW91cyBwYWxhY2VzLCBUaGUgc29sZW1uIHRlbXBsZXMsIHRoZSBncmVhdCBnbG9iZSBpdHNlbGbigJQgWWVhLCBhbGwgd2hpY2ggaXQgaW5oZXJpdOKAlHNoYWxsIGRpc3NvbHZlLCBBbmQgbGlrZSB0aGlzIGluc3Vic3RhbnRpYWwgcGFnZWFudCBmYWRlZCwgTGVhdmUgbm90IGEgcmFjayBiZWhpbmQuIFdlIGFyZSBzdWNoIHN0dWZmIEFzIGRyZWFtcyBhcmUgbWFkZSBvbiwgYW5kIG91ciBsaXR0bGUgbGlmZSBJcyByb3VuZGVkIHdpdGggYSBzbGVlcC4gU2lyLCBJIGFtIHZleGVkLiBCZWFyIHdpdGggbXkgd2Vha25lc3MuIE15IG9sZCBicmFpbiBpcyB0cm91YmxlZC4gQmUgbm90IGRpc3R1cmJlZCB3aXRoIG15IGluZmlybWl0eS4gSWYgeW91IGJlIHBsZWFzZWQsIHJldGlyZSBpbnRvIG15IGNlbGwgQW5kIHRoZXJlIHJlcG9zZS4gQSB0dXJuIG9yIHR3byBJ4oCZbGwgd2FsayBUbyBzdGlsbCBteSBiZWF0aW5nIG1pbmQu"
      }`
    });
  }
}
