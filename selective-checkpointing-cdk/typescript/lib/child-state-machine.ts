import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import {Effect, Role, ServicePrincipal} from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import {Construct} from "constructs";
import {readFileSync} from "fs";

export class ChildStateMachine extends Construct {
    public Arn: string;

    constructor(scope: Construct, id: string) {
        super(scope, id);

        // Cloud Watch Logs Policy
        const cloudWatchLogsPolicy = new iam.Policy(this, 'CloudWatchLogsPolicy', {
            statements: [
                new iam.PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: ['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
                    resources: [`arn:${cdk.Stack.of(this).partition}:logs:*:*:*`],
                })]
        });

        // Update Database Execution Role
        const updateDatabaseExecutionRole = new Role(this, 'UpdateDatabaseExecutionRole', {
            assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
        });
        updateDatabaseExecutionRole.attachInlinePolicy(cloudWatchLogsPolicy);

        // Update Database Function
        const updateDatabaseFunction = new lambda.Function(this, 'UpdateDatabaseFunction', {
                role: updateDatabaseExecutionRole,
                code: lambda.Code.fromAsset('./functions/update-database'),
                handler: "app.lambdaHandler",
                runtime: lambda.Runtime.NODEJS_16_X,
                timeout: cdk.Duration.seconds(3)
            }
        );

        // Child State Machine Execution Role
        const childStateMachineRole = new Role(this, 'ChildStateMachineRole', {
            assumedBy: new ServicePrincipal('states.amazonaws.com'),
        });
        // Long Hand - Attach Inline Policy
        // childStateMachineRole.attachInlinePolicy(new iam.Policy(this, 'ExpressStatesExecutionPolicy', {
        //     statements: [
        //         new iam.PolicyStatement({
        //             effect: Effect.ALLOW,
        //             actions: ['lambda:InvokeFunction'],
        //             resources: [updateDatabaseFunction.functionArn],
        //         })]
        // }));
        // Short Hand - Grant Invoke to Lambda
        updateDatabaseFunction.grantInvoke(childStateMachineRole);
        childStateMachineRole.attachInlinePolicy(new iam.Policy(this, 'CloudWatchLogs', {
            statements: [
                new iam.PolicyStatement({
                    effect: Effect.ALLOW,
                    actions: ['logs:CreateLogDelivery', 'logs:GetLogDelivery', 'logs:UpdateLogDelivery', 'logs:DeleteLogDelivery', 'logs:ListLogDeliveries', 'logs:PutResourcePolicy', 'logs:DescribeResourcePolicies', 'logs:DescribeLogGroups'],
                    resources: ['*'],
                })]
        }));

        // Child State Machine Log Group
        const logGroup = new logs.LogGroup(this, 'Log Group');

        // Child State Machine
        const childDefinition = readFileSync('./statemachine/statemachineChild.asl.json', 'utf-8');
        const childStateMachine = new sfn.CfnStateMachine(this, 'ChildStateMachine', {
            stateMachineType: 'EXPRESS',
            loggingConfiguration: {
                level: 'ALL',
                includeExecutionData: true,
                destinations: [{
                    cloudWatchLogsLogGroup: {
                        logGroupArn: logGroup.logGroupArn
                    }
                }]
            },
            definitionString: childDefinition,
            definitionSubstitutions: {
                UpdateDatabaseLambdaFunction: updateDatabaseFunction.functionArn
            },
            roleArn: childStateMachineRole.roleArn
        });
        this.Arn = childStateMachine.attrArn;
    }
}
