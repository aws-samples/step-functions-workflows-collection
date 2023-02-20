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
        "s3:getObject",
        "states:StartExecution"
      ],
      "Resource" : "*"
    },
    {
        "Action": [
            "dynamodb:PutItem"
        ],
        "Resource": "${aws_dynamodb_table.DDBTable.arn}",
        "Effect": "Allow"
    }
  ]
}
POLICY1
}

# Attach all the IAM policies to the equivalent roles
resource "aws_iam_role_policy_attachment" "StateMachinePolicyAttachment" {
  role       = aws_iam_role.StateMachineRole.name
  policy_arn = aws_iam_policy.StateMachinePolicy.arn
}


# Create a new DynamoDB table with all attributes and Indexes
resource "aws_dynamodb_table" "DDBTable" {
  name         = "MetaDataTable-${random_id.randomID.id}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"
  attribute {
    name = "id"
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
    TableName = aws_dynamodb_table.DDBTable.id
  }
}

# Create the AWS Step Functions State Machine
resource "aws_sfn_state_machine" "sfn_state_machine" {
  name       = "CSV-MAP-StateMachine-${random_id.randomID.id}"
  role_arn   = aws_iam_role.StateMachineRole.arn
  definition = data.template_file.SFDefinitionFile.rendered
  type       = "STANDARD"
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.MySFNLogGroup.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
  tracing_configuration {
    enabled = true
  }
}