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

# Create a zip file from the Lambda source code
data "archive_file" "LambdaZipFile" {
  type        = "zip"
  source_file = "${path.module}/lambda/app.js"
  output_path = "${path.module}/LambdaFunction.zip"
}

# Get the Managed Policy AWSLambdaBasicExecutionRole
data "aws_iam_policy" "AWSLambdaBasicExecutionRole" {
  arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Random string generator
resource "random_id" "randomID" {
  byte_length = 8
}

# Create an IAM role for the Lambda function
resource "aws_iam_role" "LambdaRole" {
  assume_role_policy = <<Role1
{
  "Version" : "2012-10-17",
  "Statement" : [
    {
      "Effect" : "Allow",
      "Principal" : {
        "Service" : "lambda.amazonaws.com"
      },
      "Action" : "sts:AssumeRole"
    }
  ]
}
Role1
}

# Create an IAM role for the Step Functions state machine
resource "aws_iam_role" "StateMachineRole" {
  assume_role_policy = <<Role2
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
Role2
}

# Create an IAM role for the EventBridge to execute Step Functions 
resource "aws_iam_role" "EventBridgeRole" {
  assume_role_policy = <<Role3
{
  "Version" : "2012-10-17",
  "Statement" : [
    {
      "Effect" : "Allow",
      "Principal" : {
        "Service" : "events.amazonaws.com"
      },
      "Action" : "sts:AssumeRole"
    }
  ]
}
Role3
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
        "cloudwatch:PutMetricData"
      ],
      "Resource" : "*"
    },
    {
      "Effect" : "Allow",
      "Action" : [
        "lambda:InvokeFunction"
      ],
      "Resource" : "${aws_lambda_function.LambdaDoWorkFunction.arn}"
    },
    {
        "Effect": "Allow",
        "Action": [
            "sns:Publish"
        ],
        "Resource": "${aws_sns_topic.NotificationTopic.arn}"
    }
  ]
}
POLICY1
}

# Attach all the IAM policies to the equivalent roles
resource "aws_iam_role_policy_attachment" "LambdaManagedPolicyAttachment" {
  role       = aws_iam_role.LambdaRole.name
  policy_arn = data.aws_iam_policy.AWSLambdaBasicExecutionRole.arn
}

resource "aws_iam_role_policy_attachment" "StateMachinePolicyAttachment" {
  role       = aws_iam_role.StateMachineRole.name
  policy_arn = aws_iam_policy.StateMachinePolicy.arn
}

# Create the Lambda function with the created Zip file of the source code
resource "aws_lambda_function" "LambdaDoWorkFunction" {
  function_name    = "Terraform-${random_id.randomID.id}-LambdaDoWorkFunction"
  filename         = data.archive_file.LambdaZipFile.output_path
  source_code_hash = filebase64sha256(data.archive_file.LambdaZipFile.output_path)
  role             = aws_iam_role.LambdaRole.arn
  handler          = "app.handler"
  runtime          = "nodejs16.x"
  timeout          = "60"
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

# State Machine definition file with the variables to replace
data "template_file" "SFDefinitionFile" {
  template = file("${path.module}/statemachines/statemachine.asl.json")
  vars = {
    TopicName        = aws_sns_topic.NotificationTopic.arn
    ProcessingLambda = aws_lambda_function.LambdaDoWorkFunction.arn
  }
}

# Create the AWS Step Functions State Machine
resource "aws_sfn_state_machine" "sfn_state_machine" {
  name       = "human-in-the-loop-${random_id.randomID.id}"
  role_arn   = aws_iam_role.StateMachineRole.arn
  definition = data.template_file.SFDefinitionFile.rendered
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.MySFNLogGroup.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
}

# Create an Log group for the Step Functions
resource "aws_cloudwatch_log_group" "MySFNLogGroup" {
  name_prefix       = "/aws/vendedlogs/states/StateMachine-terraform-"
  retention_in_days = 60
}

