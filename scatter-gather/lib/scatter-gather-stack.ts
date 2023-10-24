import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import { Construct } from 'constructs';


export class ScatterGatherStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Change this if you require a different number of responders
    const PROVIDER_COUNT = 5;
    const quoteProviderFunctionNames:string[] = new Array(PROVIDER_COUNT);

    // Create the required number of responder lambdas
    for (let i = 1; i <= PROVIDER_COUNT; i++){

      // Lambda function representing a single responder (e.g. quote look-up)
      const quoteResponder = new lambda.Function(this, 'QuoteResponder_' + i.toString(), {
        runtime: lambda.Runtime.NODEJS_18_X,
        code: lambda.Code.fromAsset('lambda'),
        handler: 'quote-responder.handler',
        environment: { 'RESPONDER_ID': i.toString()}
      });

      // Add the responder lambda function name to the array of responder lambda functions for later use
      quoteProviderFunctionNames[i - 1] = quoteResponder.functionName;
    }

     // Get a single quote by invoking the lambda function passed in from the Map function as 'quoteProvider'.
     // This requires a custom state because dynamic function names are not supported by the LambdaInvoke construct
     const getQuote = new sfn.CustomState(this, "Get quote", {
      stateJson: {
          Type: "Task",
          Resource: "arn:aws:states:::lambda:invoke",
          OutputPath: "$.Payload",
          Parameters:  {
            "FunctionName.$": "$.quoteProvider",
            "Payload": {
              "requestDescription.$": "$.requestDescription"
            }},
        }
      });
      
    // Create a map function with the list of responder lambda functions to iterate over
    const getAllQuotes = new sfn.Map(this, "Get all quotes", {
      itemsPath: "$.quoteProviders",
      resultPath: "$",
      resultSelector: {
        "requestId.$": "States.UUID()",
        "quotes.$": "$"
      },
      parameters: {
        "requestDescription.$": "$.requestDescription",
        "quoteProvider.$": "$$.Map.Item.Value"       
      },
    }).iterator(getQuote);

   
    // Create DynamoDB table to keep track of quotes requested and received
    const quoteTable = new dynamodb.Table(this, 'Quotes', {
      partitionKey: { name: 'requestId', type: dynamodb.AttributeType.STRING  },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      encryption: dynamodb.TableEncryption.DEFAULT,
    });

    // Create DynamoDB PutItem task to write the result to DDB
    const ddbPutItemTask = new tasks.DynamoPutItem(this, "Save quotes to DynamoDB", {
      table: quoteTable,
      item:{
        requestId: tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt("$.requestId")),
        quotes: tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt("States.JsonToString($.quotes)"))
      }
    });

     // Step function definition
     const stateMachine = new sfn.StateMachine(this, 'StateMachine', {
      definitionBody: sfn.DefinitionBody.fromChainable(getAllQuotes.next(ddbPutItemTask)),
      timeout: cdk.Duration.minutes(5)
    });

    // We need to manually grant permission to invoke lambdas to the step function execution role
    // (this would be done automatically if using the LambdaInvoke construct)
    stateMachine.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['lambda:InvokeFunction'],
      resources: ['*']
    }));

    // For convenience, create an output object with a sample request message
    const outputJson = JSON.stringify({
      requestDescription: "Flight LHR - JFK, 01/01/2025",
      quoteProviders: quoteProviderFunctionNames});

    new cdk.CfnOutput(this, "testRequest", {
      value: outputJson,
      exportName: "testRequest",
    });

  }
}