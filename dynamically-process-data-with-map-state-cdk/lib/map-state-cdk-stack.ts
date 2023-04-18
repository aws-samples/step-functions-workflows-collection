import { Construct } from 'constructs';
import {
  Aws,
  Stack,
  StackProps,
  aws_lambda as lambda,
  aws_iam as iam,
  aws_sqs as sqs,
  aws_dynamodb as dynamodb,
  aws_sns as sns,
  aws_kms as kms,
  aws_stepfunctions_tasks as tasks,
  aws_stepfunctions as sfn,
  aws_sns_subscriptions as subscriptions,
  Duration,
  CfnParameter,
  CfnOutput
} from 'aws-cdk-lib';
export class MapStateCdkStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    //During deployment, this paramter will prompt for the email address of the user to receive notifications of SQS messages
    const userEmailAddress = new CfnParameter(this, "UserEmailAddress", {
      type: "String",
      description: "Enter the email address that will receive SQS message notifications.",
      default: "user@example.com"
    });

    //SNS topic for notification
    const snsKey = kms.Alias.fromAliasName(this, "snsKey", "alias/aws/sns");
    const snsTopic = new sns.Topic(this, "NotificationTopic", {
      topicName: `${Aws.STACK_NAME}-NotificationTopic`,
      masterKey: snsKey
    });

    //Subcription to the SNS topic
    snsTopic.addSubscription(new subscriptions.EmailSubscription(userEmailAddress.valueAsString));
    
    //DynamoDB table
    const dynamoDBTable = new dynamodb.Table(this, "MessagesTable", {
      partitionKey: { name: "MessageId", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1
    });
    //SQS queue 
    const sqsQueue = new sqs.Queue(this, "Queue");
    //Lambda functions execution role
    const lambdaFunctionsExecRole = new iam.Role(this, "LambdaFunctionsExecRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
    });
    lambdaFunctionsExecRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaSQSQueueExecutionRole"));

    //Lambda function that reads from SQS queue
    const readFromSQSLambda = new lambda.Function(this, "Read from SQS", {
      runtime: lambda.Runtime.NODEJS_14_X,
      handler: "read-from-sqs.lambda_handler",
      code: lambda.Code.fromAsset("./functions/read-from-sqs"),
      environment: {
        "SQS_QUEUE_URL": sqsQueue.queueUrl
      },
      role: lambdaFunctionsExecRole,
      timeout: Duration.seconds(60)
    });

    //Lambda function that deletes proccessed messages from the SQS queue
    const deleteFromSQSLambda = new lambda.Function(this, "Delete from sqs", {
      runtime: lambda.Runtime.NODEJS_14_X,
      handler: "delete-from-sqs.lambda_handler",
      code: lambda.Code.fromAsset("./functions/delete-from-sqs"),
      environment: {
        "SQS_QUEUE_URL": sqsQueue.queueUrl
      },
      role: lambdaFunctionsExecRole,
      timeout: Duration.seconds(20)
    });


    //Building step function statemachine tasks 
    const readMessagesFromSQS = new tasks.LambdaInvoke(this, "Read messages from SQS queue", {
      lambdaFunction: readFromSQSLambda,
      outputPath: sfn.JsonPath.stringAt("$.Payload")
    });

    const areThereMessagesToProcess = new sfn.Choice(this, "Are there messages to process?");
    const thereAreNoMessagesToProcess = sfn.Condition.stringEquals("$", "No messages");

    const writeMessageToDynamoDB = new tasks.DynamoPutItem(this, "Write message to DynamoDB", {
      table: dynamoDBTable,
      item: {
        MessageId: tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt("$.MessageDetails.MessageId")),
        Body: tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt("$.MessageDetails.Body"))
      },
      resultPath: sfn.JsonPath.DISCARD,
      returnConsumedCapacity: tasks.DynamoConsumedCapacity.TOTAL
    });

    const deleteMessagesFromSQS = new tasks.LambdaInvoke(this, "Remove messages from SQS queue", {
      lambdaFunction: deleteFromSQSLambda,
      inputPath: sfn.JsonPath.stringAt("$.MessageDetails"),
      resultPath: sfn.JsonPath.DISCARD,
      payload: sfn.TaskInput.fromObject({
        ReceiptHandle: sfn.JsonPath.stringAt("$.ReceiptHandle")
      })
    });


    const publishMessageToSNSTopic = new tasks.SnsPublish(this, "Publish message to SNS topic", {
      topic: snsTopic,
      inputPath: sfn.JsonPath.stringAt("$.MessageDetails"),
      message: sfn.TaskInput.fromJsonPathAt("$.Body"),
      subject: "Message from Step Functions!"
    });

    const processMessagesMapState = new sfn.Map(this, "Process Messages", {
      itemsPath: sfn.JsonPath.stringAt("$"),
      parameters: {
        MessageNumber: sfn.JsonPath.stringAt("$$.Map.Item.Index"),
        MessageDetails: sfn.JsonPath.stringAt("$$.Map.Item.Value")
      }
    });

    const finish = new sfn.Succeed(this, "Finish");
    const mapStateChain = sfn.Chain.start(writeMessageToDynamoDB).next(deleteMessagesFromSQS).next(publishMessageToSNSTopic);
    processMessagesMapState.iterator(mapStateChain);

    const stateMachineChainDefinition = sfn.Chain.start(readMessagesFromSQS).next(areThereMessagesToProcess.when(thereAreNoMessagesToProcess, finish).otherwise(processMessagesMapState.next(finish)));

    const mapStateStateMachine = new sfn.StateMachine(this, "Map State State Machine", {
      definition: stateMachineChainDefinition
    });

     //outputs
     const stateMachineArn = new CfnOutput(this, "stateMachineArn", {
      value: mapStateStateMachine.stateMachineArn,
    });
  }
}
