{
  "StartAt": "ListFiles",
  "States": {
    "ListFiles": {
      "Next": "CopyFiles",
      "Retry": [
        {
          "ErrorEquals": [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException"
          ],
          "IntervalSeconds": 2,
          "MaxAttempts": 6,
          "BackoffRate": 2
        }
      ],
      "Type": "Task",
      "OutputPath": "$.Payload",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "${ListFilesFunctionArn}",
        "Payload.$": "$"
      }
    },
    "CopyFiles": {
      "End": true,
      "Type": "Task",
      "Resource": "arn:aws:states:::ecs:runTask.sync",
      "Parameters": {
        "Cluster": "${WorkflowAppCLuster}",
        "TaskDefinition": "workflowAppCdkStackWorkflowAppTaskDef",
        "NetworkConfiguration": {
          "AwsvpcConfiguration": {
            "Subnets": [
              "subnet-000143b27d0d956bb",
              "subnet-00d01771aafa85798",
              "subnet-0dcd191a091464f61"
            ],
            "SecurityGroups": [
              "sg-058a3db93525d7ef7"
            ]
          }
        },
        "Overrides": {
          "ContainerOverrides": [
            {
              "Name": "WorkflowAppContainer",
              "Command": [
                "dotnet",
                "CopyFilesTask.dll"
              ],
              "Environment": [
                {
                  "Name": "Input",
                  "Value.$": "States.JsonToString($)"
                }
              ]
            }
          ]
        },
        "LaunchType": "FARGATE"
      }
    }
  }
}