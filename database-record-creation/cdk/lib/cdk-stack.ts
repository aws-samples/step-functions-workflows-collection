import * as cdk from 'aws-cdk-lib';
import * as stepfunctions from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export class CdkStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    /** PARAMETERS */
    const accountId = cdk.Stack.of(this).account.toString();
    const projectName = new cdk.CfnParameter(this, 'projectName', {
      type: 'String',
      description: 'Prefix used to identify project and resources',
      default: 'validateRecord'
    });
    
    // DynamoDB
    const dynamoDB = new cdk.aws_dynamodb.Table(this, 'DynamoDB', {
      tableName: `${accountId}-${projectName.value}-dynamo-table`,
      partitionKey: { name: 'id', type: cdk.aws_dynamodb.AttributeType.STRING  },
      deletionProtection: false,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // Lambda to validate
    const validateFunction = new lambda.Function(this, 'Lambda', { 
      functionName: `${accountId}-${projectName.value}-validate-lambda`,
      runtime: cdk.aws_lambda.Runtime.NODEJS_14_X,
      code: cdk.aws_lambda.Code.fromAsset('code'),
      handler: 'validatePayload.handler',
    });


    // workflow
    // 01-invoke the lambda
    const invokeValidateLambda = new tasks.LambdaInvoke(this, 'Validate Task', {       
      lambdaFunction: validateFunction,
    });

    // 02-success
    const jobSucceed = new stepfunctions.Pass(this, 'Job Succeed', {});

    // 03-failure
    const jobFailed = new stepfunctions.Fail(this, 'Job Failed', {
      cause: 'Payload is not valid',
      error: 'One or more fields are not valid',

    });    

    // 04-dynamodb put item
    const dynamoPutItem = new tasks.DynamoPutItem(this, 'Create record', { 
      table: dynamoDB,
      item: {
        id: tasks.DynamoAttributeValue.fromString(stepfunctions.JsonPath.stringAt('$.Payload.body.id')),
        firstname: tasks.DynamoAttributeValue.fromString(stepfunctions.JsonPath.stringAt('$.Payload.body.firstname')),
        email: tasks.DynamoAttributeValue.fromString(stepfunctions.JsonPath.stringAt('$.Payload.body.email')),
      }      
    });

    dynamoPutItem.next(jobSucceed);

    // 05-choicestate
    const choicestate = new stepfunctions.Choice(this, 'Is Payload valid?');
    choicestate
      .when(stepfunctions.Condition.booleanEquals('$.Payload.body.isValid', true), dynamoPutItem)
      .otherwise(jobFailed);
    
    // 99-state machine
    const workflow = new stepfunctions.StateMachine(this, 'Workflow', { 
      stateMachineName: `${accountId}-${projectName.value}-workflow`,
      definition: invokeValidateLambda
        .next(choicestate)
    });
  }

}
