import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import { Construct } from 'constructs';
import { get } from 'http';


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

    // Create a MapState, Iterator and ErrorHandler as a CustomState. This could be done in smaller, more CDK-friendly chunks, but there is 
    // an outstanding CDK bug that prevents the correct chaining of the ErrorHandler (https://github.com/aws/aws-cdk/issues/25798)
    const getQuotes = new sfn.CustomState(this, "Get quotes", {
    stateJson: {
      "Type": "Map",
      "ResultPath": "$",
      "Next": "Save quotes to DynamoDB",
      "Parameters": {
        "requestDescription.$": "$.requestDescription",
        "quoteProvider.$": "$$.Map.Item.Value"
      },
      "ResultSelector": {
        "requestId.$": "States.UUID()",
        "quotes.$": "$"
      },
      "Iterator": {
        "StartAt": "Get quote",
        "States": {
          "Get quote": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "OutputPath": "$.Payload",
            "Parameters": {
              "FunctionName.$": "$.quoteProvider",
              "Payload": {
                "requestDescription.$": "$.requestDescription"
              }
            },
            "Catch": [
              {
                "ErrorEquals": [
                  "States.ALL"
                ],
                "Next": "ErrorHandler"
              }
            ],
            "End": true
          },
          "ErrorHandler": {
            "Type": "Pass",
            "Parameters": {
              "quote.$": "$"
            },
            "End": true
          }
        }
      },
      "ItemsPath": "$.quoteProviders"
    }});
   
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

     // Step function definition combining the MapState and the DynamoDB PutItem
     const stateMachine = new sfn.StateMachine(this, 'StateMachine', {
      definitionBody: sfn.DefinitionBody.fromChainable(getQuotes.next(ddbPutItemTask)),
      timeout: cdk.Duration.minutes(5)
    });

    // We need to manually grant permission to invoke lambdas to the step function execution role
    // (this would be done automatically if using the LambdaInvoke CDK class, but we cannot do this because of the dynamic lambda function name)
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