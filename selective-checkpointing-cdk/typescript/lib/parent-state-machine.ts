import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import {Effect, Role, ServicePrincipal} from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import {SqsEventSource} from "aws-cdk-lib/aws-lambda-event-sources";
import * as sns from "aws-cdk-lib/aws-sns";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import {Construct} from "constructs";
import {readFileSync} from "fs";

export class ParentStateMachine extends Construct {
    public Arn: string;

    constructor(scope: Construct, id: string, childStateMachineArn: string) {
        super(scope, id);

        // SNS Topic
        const snsTopic = new sns.Topic(this, 'ShipPackageLambdaFunction');

        // SQS Queue DLQ
        const sqsQueueDLQ = new sqs.Queue(this, 'SQLQueueDLQ', {
            deliveryDelay: cdk.Duration.seconds(0),
            visibilityTimeout: cdk.Duration.seconds(30)
        });

        // SQS Queue
        const sqsQueue = new sqs.Queue(this, 'SQLQueue', {
            deliveryDelay: cdk.Duration.seconds(0),
            visibilityTimeout: cdk.Duration.seconds(30),
            deadLetterQueue: {
                maxReceiveCount: 1,
                queue: sqsQueueDLQ,
            }
        });

        // Cloud Watch Logs Policy
        const cloudWatchLogsPolicy = new iam.Policy(this, 'CloudWatchLogsPolicy', {
            statements: [
                new iam.PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
                    resources: [`arn:${cdk.Stack.of(this).partition}:logs:*:*:*`],
                })]
        });

        // Ship Package Execution Role
        const shipPackageExecutionRole = new Role(this, 'ShipPackageExecutionRole', {
            assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
        });
        shipPackageExecutionRole.attachInlinePolicy(new iam.Policy(this, 'SQSReceiveMessagePolicy', {
            statements: [
                new iam.PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: ['sqs:ReceiveMessage', 'sqs:DeleteMessage', 'sqs:GetQueueAttributes', 'sqs:ChangeMessageVisibility'],
                    resources: [sqsQueue.queueArn],
                })]
        }));
        shipPackageExecutionRole.attachInlinePolicy(cloudWatchLogsPolicy);
        shipPackageExecutionRole.attachInlinePolicy(new iam.Policy(this, 'ShipPackageStatesExecutionPolicy', {
            statements: [
                new iam.PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: ['states:SendTaskSuccess','states:SendTaskFailure'],
                    resources: ['*'],
                })]
        }));

        // Ship Package Function
        const shiftPackageFunction = new lambda.Function(this, 'ShipPackageFunction', {
                role: shipPackageExecutionRole,
                code: lambda.Code.fromAsset('./functions/ship-package'),
                handler: "app.lambdaHandler",
                runtime: lambda.Runtime.NODEJS_16_X,
                timeout: cdk.Duration.seconds(8)
            }
        );
        const eventSource = new SqsEventSource(sqsQueue, {
            batchSize: 10,
            enabled: true
        });
        shiftPackageFunction.addEventSource(eventSource);

        // Parent State Machine Execution Role
        const parentStateMachineRole = new Role(this, 'ParentStateMachineRole', {
            assumedBy: new ServicePrincipal('states.amazonaws.com'),
        });
        // Long Hand - Attach Inline Policy
        // parentStateMachineRole.attachInlinePolicy(new iam.Policy(this, 'SNSPublishPolicy', {
        //     statements: [
        //         new iam.PolicyStatement({
        //             effect: Effect.ALLOW,
        //             actions: ['sns:Publish'],
        //             resources: [snsTopic.topicArn],
        //         })]
        // }));
        // Short Hand - Grant Publish to SNS
        snsTopic.grantPublish(parentStateMachineRole);
        // Long Hand - Attach Inline Policy
        // parentStateMachineRole.attachInlinePolicy(new iam.Policy(this, 'SQSSendMessagePolicy', {
        //     statements: [
        //         new iam.PolicyStatement({
        //             effect: Effect.ALLOW,
        //             actions: ['sqs:SendMessage'],
        //             resources: [sqsQueue.queueArn],
        //         })]
        // }));
        // Short Hand - Grant SendMessage to SQS
        sqsQueue.grantSendMessages(parentStateMachineRole);
        parentStateMachineRole.attachInlinePolicy(new iam.Policy(this, 'StatesExecutionPolicy', {
            statements: [
                new iam.PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: ['states:StartExecution','states:DescribeExecution','states:StopExecution'],
                    resources: ['*'],
                }),
                new iam.PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: ['events:PutTargets','events:PutRule','events:DescribeRule'],
                    resources: [`arn:${cdk.Stack.of(this).partition}:events:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:rule/StepFunctionsGetEventsForStepFunctionsExecutionRule`],
                })],
        }));

        // Parent State Machine
        const parentDefinition = readFileSync('./statemachine/statemachineParent.asl.json', 'utf-8');
        const parentStateMachine = new sfn.CfnStateMachine(this, 'ParentStateMachine', {
            definitionString: parentDefinition,
            definitionSubstitutions: {
                sendtoSNSArn: snsTopic.topicArn,
                sqsQueueUrl: sqsQueue.queueUrl,
                SelectiveCheckpointingExpressStateMachineArn: childStateMachineArn,
            },
            roleArn: parentStateMachineRole.roleArn
        });
        this.Arn = parentStateMachine.attrArn;
    }
}
