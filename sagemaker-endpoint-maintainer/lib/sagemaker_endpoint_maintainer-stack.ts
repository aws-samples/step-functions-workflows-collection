import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class SagemakerEndpointMaintainerStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const stateMachine = new cdk.aws_stepfunctions.StateMachine(
      this,
      'SagemakerMaintainer',
      {
        definitionBody: cdk.aws_stepfunctions.DefinitionBody.fromString(`
        {
          "Comment": "A description of my state machine",
          "StartAt": "EventSource",
          "States": {
            "EventSource": {
              "Type": "Choice",
              "Choices": [
                {
                  "And": [
                    {
                      "Variable": "$.source",
                      "StringEquals": "aws.cloudwatch"
                    },
                    {
                      "Variable": "$.detail.configuration.metrics[0].metricStat.metric.namespace",
                      "StringEquals": "AWS/SageMaker"
                    },
                    {
                      "Or": [
                        {
                          "Variable": "$.detail.state.value",
                          "StringEquals": "ALARM"
                        },
                        {
                          "Variable": "$.detail.state.value",
                          "StringEquals": " INSUFFICIENT_DATA"
                        }
                      ]
                    }
                  ],
                  "Next": "DeleteEndpoint"
                },
                {
                  "Variable": "$.source",
                  "StringEquals": "aws.sagemaker",
                  "Next": "SagemakerEventType"
                }
              ],
              "Default": "OtherCalls"
            },
            "SagemakerEventType": {
              "Type": "Choice",
              "Choices": [
                {
                  "And": [
                    {
                      "Variable": "$.detail.EndpointStatus",
                      "StringEquals": "DELETED"
                    }
                  ],
                  "Next": "DeleteAlarms"
                },
                {
                  "And": [
                    {
                      "Variable": "$.detail.EndpointStatus",
                      "StringEquals": "IN_SERVICE"
                    },
                    {
                      "Variable": "$.detail.Tags.auto-maintain",
                      "StringEquals": "true"
                    }
                  ],
                  "Next": "Wait"
                }
              ],
              "Default": "OtherCalls"
            },
            "Wait": {
              "Type": "Wait",
              "Seconds": 300,
              "Next": "PutMetricAlarm"
            },
            "PutMetricAlarm": {
              "Type": "Task",
              "Parameters": {
                "AlarmName.$": "$.detail.EndpointName",
                "Namespace": "AWS/SageMaker",
                "MetricName": "Invocations",
                "Dimensions": [
                  {
                    "Name": "EndpointName",
                    "Value.$": "$.detail.EndpointName"
                  },
                  {
                    "Name": "VariantName",
                    "Value": "AllTraffic"
                  }
                ],
                "ComparisonOperator": "LessThanOrEqualToThreshold",
                "DatapointsToAlarm": 3,
                "EvaluationPeriods": 3,
                "Period": 300,
                "Statistic": "Maximum",
                "Threshold": 0,
                "TreatMissingData": "breaching"
              },
              "Resource": "arn:aws:states:::aws-sdk:cloudwatch:putMetricAlarm",
              "End": true
            },
            "DeleteAlarms": {
              "Type": "Task",
              "Parameters": {
                "AlarmNames.$": "States.Array($.detail.EndpointName)"
              },
              "Resource": "arn:aws:states:::aws-sdk:cloudwatch:deleteAlarms",
              "End": true
            },
            "DeleteEndpoint": {
              "Type": "Task",
              "End": true,
              "Parameters": {
                "EndpointName.$": "$.detail.alarmName"
              },
              "Resource": "arn:aws:states:::aws-sdk:sagemaker:deleteEndpoint"
            },
            "OtherCalls": {
              "Type": "Pass",
              "End": true
            }
          }
        }
        `),
      },
    );

    stateMachine.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: [
          'cloudwatch:putMetricAlarm',
          'cloudwatch:DeleteAlarms',
          'sagemaker:DeleteEndpoint',
        ],
        resources: ['*'],
      }),
    );

    const eventsInvokeSfnRole = new cdk.aws_iam.Role(this, 'Role', {
      assumedBy: new cdk.aws_iam.ServicePrincipal('events.amazonaws.com'),
      description: 'Allow Execution of States Function from EventBridge',
    });
    eventsInvokeSfnRole.addToPolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: ['states:StartExecution'],
        resources: [stateMachine.stateMachineArn],
      }),
    );
    const stateMachineBind: cdk.aws_events.IRuleTarget = {
      bind: () => ({
        id: '',
        arn: stateMachine.stateMachineArn,
        role: eventsInvokeSfnRole,
      }),
    };

    // eventbridge rule that notifies when a Sagemaker Endpoint is created
    const inServiceRule = new cdk.aws_events.Rule(
      this,
      'sagemaker-endpoint-inservice',
      {
        eventPattern: {
          source: ['aws.sagemaker'],
          detailType: ['SageMaker Endpoint State Change'],
          detail: {
            EndpointStatus: [
              {
                prefix: 'IN_SERVICE',
              },
            ],
          },
        },
        targets: [stateMachineBind],
      },
    );

    // eventbridge rule that notifies when a Sagemaker Endpoint is deleted
    const deletedRule = new cdk.aws_events.Rule(
      this,
      'sagemaker-endpoint-deleted',
      {
        eventPattern: {
          source: ['aws.sagemaker'],
          detailType: ['SageMaker Endpoint State Change'],
          detail: {
            EndpointStatus: [
              {
                prefix: 'DELETED',
              },
            ],
          },
        },
        targets: [stateMachineBind],
      },
    );

    // eventbridge rule that notifies when an endpoint is idle
    const idleEndpoint = new cdk.aws_events.Rule(
      this,
      'sagemaker-endpoint-idle',
      {
        eventPattern: {
          source: ['aws.cloudwatch'],
          detailType: ['CloudWatch Alarm State Change'],
        },
        targets: [stateMachineBind],
      },
    );
  }
}
