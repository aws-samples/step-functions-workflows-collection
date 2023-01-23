import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Duration } from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as path from 'path';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';

export class WorkflowmonitorStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props ? : cdk.StackProps) {
    super(scope, id, props);

    // Define name for EventBridge event bus
    const eventBusName = "workflow-montoring-bus";
    // Define message prefix which triggers the error handling Lambda function
    const errorEventPrefix = "WorkflowError";
    // Define message prefix which triggers the Lamba function to shutdown workflow monitoring
    const stopEventPrefix = "StopWorkflowMonitoring";

    // Create EventBridge event bus
    const workflowEventBus = new events.EventBus(this, 'workflowEventBus', {
      eventBusName: eventBusName
    });

    // Create Lambda functions to handle stop monitoring events and error events
    const monitoringErrorHandler = new lambda.Function(this, 'monitoringErrorHandler', {
      runtime: lambda.Runtime.NODEJS_18_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, 'lambda-source/workflow-event-error-handler/')),
    });

    const monitoringStopHandler = new lambda.Function(this, 'monitoringStopHandler', {
      runtime: lambda.Runtime.NODEJS_18_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, 'lambda-source/workflow-event-stop-handler/')),
    });

    // Add EventBridge rules to invoke the Lambda functions
    const monitoringStopRule = new events.Rule(this, 'monitoringStopRule', {
      eventBus: workflowEventBus,
      eventPattern: {
        "detail": {
          "message": [{
            "prefix": stopEventPrefix
          }]
        }
      },
    });
    monitoringStopRule.addTarget(new targets.LambdaFunction(monitoringStopHandler, {
      maxEventAge: cdk.Duration.hours(1),
      retryAttempts: 2,
    }));

    const monitoringErrorRule = new events.Rule(this, 'monitoringErrorRule', {
      eventBus: workflowEventBus,
      eventPattern: {
        "detail": {
          "message": [{
            "prefix": errorEventPrefix
          }]
        }
      },
    });
    monitoringErrorRule.addTarget(new targets.LambdaFunction(monitoringErrorHandler, {
      maxEventAge: cdk.Duration.hours(1),
      retryAttempts: 2,
    }));

    // Create DynamoDB table to keep track of active workflow monitoring tasks within runnin step functios
    const workflowMonitoringTable = new dynamodb.Table(this, 'workflowMonitoringTable', {
      partitionKey: { name: 'workflowkey', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      encryption: dynamodb.TableEncryption.DEFAULT,
    });

    // Grant permissions to the Lambda functions and set environment variables
    workflowMonitoringTable.grantReadWriteData(monitoringStopHandler);
    workflowMonitoringTable.grantReadWriteData(monitoringErrorHandler);
    monitoringStopHandler.addEnvironment("TABLENAME", workflowMonitoringTable.tableName);
    monitoringErrorHandler.addEnvironment("TABLENAME", workflowMonitoringTable.tableName);

    // Define a sample Step Function with a monitoring task
    const waitTask = new sfn.Wait(this, 'YourWorkGoesHere', {
      time: sfn.WaitTime.duration(Duration.seconds(20)),
    });

    const startMonitoringTask = new tasks.CallAwsService(this, 'StartWorkflowMonitoring', {
      integrationPattern: sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
      service: 'dynamodb',
      action: 'putItem',
      iamResources: [workflowMonitoringTable.tableArn],
      parameters: {
        TableName: workflowMonitoringTable.tableName,
        Item: {
          workflowkey: { "S.$": '$.workflowkey' },
          tasktoken: { "S.$": '$$.Task.Token' },
        },
      }
    });

    const stopMonitoringTask = new tasks.EventBridgePutEvents(this, 'StopWorkflowMontoring', {
      integrationPattern: sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
      entries: [{
        detail: sfn.TaskInput.fromObject({
          message: stopEventPrefix,
          tasktoken: sfn.JsonPath.taskToken,
          workflowkey: sfn.JsonPath.stringAt('$.workflowkey'),
        }),
        eventBus: workflowEventBus,
        detailType: 'WorkflowMonitoring',
        source: 'workflow.sfn',
      }],
    });

    const parallelExecution = new sfn.Parallel(this, 'executeParallel')
      .branch(startMonitoringTask)
      .branch(waitTask.next(stopMonitoringTask));


    const stateMachine = new sfn.StateMachine(this, 'WorkflowStateMachine', {
      definition: parallelExecution,
    });

    // Grant the Lambda functions permissions to send task responses to Step Functions
    stateMachine.grantTaskResponse(monitoringStopHandler);
    stateMachine.grantTaskResponse(monitoringErrorHandler);

  }
}
