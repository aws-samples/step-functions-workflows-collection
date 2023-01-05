terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  profile = "default"
  region  = var.region
}

# Random string generator
resource "random_id" "randomID" {
  byte_length = 8
}

# Create an IAM role for the Step Functions state machine
resource "aws_iam_role" "StateMachineRole" {
  assume_role_policy = <<Role1
{
  "Version" : "2012-10-17",
  "Statement" : [
    {
      "Effect" : "Allow",
      "Principal" : {
        "Service" : "states.amazonaws.com"
      },
      "Action" : "sts:AssumeRole"
    }
  ]
}
Role1
}

# Create an IAM role for API Gateway
resource "aws_iam_role" "APIGWRole" {
  assume_role_policy = <<Role2
{
  "Version" : "2012-10-17",
  "Statement" : [
    {
      "Effect" : "Allow",
      "Principal" : {
        "Service" : "apigateway.amazonaws.com"
      },
      "Action" : "sts:AssumeRole"
    }
  ]
}
Role2
}

# Create an IAM policy for the Step Functions state machine
resource "aws_iam_policy" "StateMachinePolicy" {
  policy = <<POLICY1
{
  "Version" : "2012-10-17",
  "Statement" : [
    {
      "Effect" : "Allow",
      "Action" : [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:CreateLogDelivery",
        "logs:GetLogDelivery",
        "logs:UpdateLogDelivery",
        "logs:DeleteLogDelivery",
        "logs:ListLogDeliveries",
        "logs:PutResourcePolicy",
        "logs:DescribeResourcePolicies",
        "logs:DescribeLogGroups",
        "cloudwatch:PutMetricData",
        "comprehend:DetectSentiment"
      ],
      "Resource" : "*"
    },
    {
        "Effect": "Allow",
        "Action": [
            "sns:Publish"
        ],
        "Resource": "${aws_sns_topic.NotificationTopic.arn}"
    },
    {
        "Action": [
            "dynamodb:PutItem"
        ],
        "Resource": "${aws_dynamodb_table.FormDataTable.arn}",
        "Effect": "Allow"
    }
  ]
}
POLICY1
}

# Create an IAM policy for API Gateway to write to create an EventBridge event
resource "aws_iam_policy" "APIGWPolicy" {
  policy = <<POLICY2
{
  "Version" : "2012-10-17",
  "Statement" : [
    {
      "Effect" : "Allow",
      "Action" : [
        "states:StartSyncExecution"
      ],
      "Resource" : "${aws_sfn_state_machine.sfn_state_machine.arn}"
    }
  ]
}
POLICY2
}

# Attach all the IAM policies to the equivalent roles
resource "aws_iam_role_policy_attachment" "StateMachinePolicyAttachment" {
  role       = aws_iam_role.StateMachineRole.name
  policy_arn = aws_iam_policy.StateMachinePolicy.arn
}

resource "aws_iam_role_policy_attachment" "APIGWPolicyAttachment" {
  role       = aws_iam_role.APIGWRole.name
  policy_arn = aws_iam_policy.APIGWPolicy.arn
}

# Create the SNS topic & subscription
resource "aws_sns_topic" "NotificationTopic" {
  name_prefix = "NotificationTopic"
}

resource "aws_sns_topic_subscription" "NotificationTopicSub" {
  topic_arn = aws_sns_topic.NotificationTopic.arn
  protocol  = "email"
  endpoint  = var.email
}

# Create a new DynamoDB table with all attributes and Indexes
resource "aws_dynamodb_table" "FormDataTable" {
  name         = "FormDataTable-${random_id.randomID.id}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "formId"
  attribute {
    name = "formId"
    type = "S"
  }
}

# Create a Log group for the Step Functions state machine
resource "aws_cloudwatch_log_group" "MySFNLogGroup" {
  name_prefix       = "/aws/vendedlogs/states/StateMachine-terraform-"
  retention_in_days = 60
}

# State Machine definition file with the variables to replace
data "template_file" "SFDefinitionFile" {
  template = file("${path.module}/statemachines/statemachine.asl.json")
  vars = {
    DDBTable  = aws_dynamodb_table.FormDataTable.id
    TopicName = aws_sns_topic.NotificationTopic.arn
  }
}

# Create the AWS Step Functions State Machine
resource "aws_sfn_state_machine" "sfn_state_machine" {
  name       = "ProcessFormStateMachineExpressSync-${random_id.randomID.id}"
  role_arn   = aws_iam_role.StateMachineRole.arn
  definition = data.template_file.SFDefinitionFile.rendered
  type       = "EXPRESS"
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.MySFNLogGroup.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
  tracing_configuration {
    enabled = true
  }
}

# API Gateway definition file with the variables to replace
data "template_file" "APIDefinitionFile" {
  template = file("${path.module}/api.yaml")
  vars = {
    APIGWRole       = aws_iam_role.APIGWRole.arn
    StateMachineArn = aws_sfn_state_machine.sfn_state_machine.arn
  }
}

# Create an API Gateway HTTP with integration with EventBridge
resource "aws_apigatewayv2_api" "MyApiGatewayHTTPApi" {
  name          = "processFormExample-${random_id.randomID.id}"
  protocol_type = "HTTP"
  body          = data.template_file.APIDefinitionFile.rendered
}

# Create an API Gateway Stage with automatic deployment
resource "aws_apigatewayv2_stage" "MyApiGatewayHTTPApiStage" {
  api_id      = aws_apigatewayv2_api.MyApiGatewayHTTPApi.id
  name        = "$default"
  auto_deploy = true
}