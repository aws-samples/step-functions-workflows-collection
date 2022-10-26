
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>4.0"
    }
  }
}

provider "aws" {
  region  = var.region
  profile = var.aws_profile_name

}

locals {
  project_name = "stepfunctions-sampleproject"

}

data "aws_caller_identity" "caller" {}
data "aws_partition" "partition" {}

#Create the Event Bus
resource "aws_cloudwatch_event_bus" "bus" {
  name = "${local.project_name}-eventbus"
}

#Create the Event Bridge Rule
resource "aws_cloudwatch_event_rule" "rule" {
  name           = "${local.project_name}-rule"
  description    = "Step Function Test Rule"
  event_pattern  = <<EOL
    {"source":["my.statemachine"],"detail-type":["MessageFromStepFunctions"]}
EOL
  event_bus_name = aws_cloudwatch_event_bus.bus.name
}

#Add Lambda target to bus
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule           = aws_cloudwatch_event_rule.rule.name
  arn            = aws_lambda_function.sfn_lambda.arn
  event_bus_name = aws_cloudwatch_event_bus.bus.name
}

# Add SQS target to bus
resource "aws_cloudwatch_event_target" "sqs_target" {
  rule           = aws_cloudwatch_event_rule.rule.name
  arn            = aws_sqs_queue.queue.arn
  event_bus_name = aws_cloudwatch_event_bus.bus.name
}

# Add SNS Target to bus
resource "aws_cloudwatch_event_target" "sns_target" {
  rule           = aws_cloudwatch_event_rule.rule.name
  arn            = aws_sns_topic.topic.arn
  event_bus_name = aws_cloudwatch_event_bus.bus.name
}

## Create the State Machine

resource "aws_sfn_state_machine" "state_machine" {
  name       = "${local.project_name}-sfn"
  type       = "STANDARD"
  definition = file("statemachine/statemachine.asl.json")
  role_arn   = aws_iam_role.sfn_role.arn

}

#Step Function Role
resource "aws_iam_role" "sfn_role" {
  name = "${local.project_name}-sfn-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "states.amazonaws.com"
        }
      },
    ]
  })
  inline_policy {
    name = "allow_put_eb"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
      "Sid": "Stmt1665517897412",
      "Action": [
        "events:PutEvents"
      ],
      "Effect": "Allow",
      "Resource": "${aws_cloudwatch_event_bus.bus.arn}"
    }
      ]
    })
  }
}

#Create the lambda trust policy
resource "aws_iam_role" "lambda_role" {
  name               = "${local.project_name}-lambda-role"
  assume_role_policy = <<EOF
    {
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
inline_policy {
  name = "default_policy"
  policy =jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
      "Sid": "putcW",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Effect": "Allow",
      "Resource": "arn:${data.aws_partition.partition.partition}:logs:${var.region}:${data.aws_caller_identity.caller.account_id}:*"
    }
    ]


})

}
}

#Zip up the function for deployment
data "archive_file" "func" {
  type        = "zip"
  source_file = "src/handler.py"
  output_path = "${path.module}/files/func.zip"
}

#Create the CloudWatch Logs log group with 1 day retention
resource "aws_cloudwatch_log_group" "log_group" {
  name = "/aws/lambda/${local.project_name}-function"
  retention_in_days = 1
}

#Create the lambda function target
resource "aws_lambda_function" "sfn_lambda" {
  function_name = "${local.project_name}-function"
  role          = aws_iam_role.lambda_role.arn
  filename      = "${path.module}/files/func.zip"
  handler       = "handler.handler"
  source_code_hash = data.archive_file.func.output_base64sha256
  runtime          = "python3.9"
}

#Lambda Permission for EB invocation
resource "aws_lambda_permission" "allow_eb" {
  statement_id  = "AllowEBInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sfn_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.rule.arn

}

# Create the SQS target queue
resource "aws_sqs_queue" "queue" {
  name = "${local.project_name}-queue"
}

# SQS Queue Policy allowing EB to publish events. 
resource "aws_sqs_queue_policy" "queue_policy" {
  queue_url = aws_sqs_queue.queue.id
  policy    = data.aws_iam_policy_document.sqs_policy_doc.json
}

#SNS Topic
resource "aws_sns_topic" "topic" {
  name = "${local.project_name}-topic"

}
# Create the SNS publishing policy 
resource "aws_sns_topic_policy" "topic_policy" {
  arn    = aws_sns_topic.topic.arn
  policy = data.aws_iam_policy_document.sns_policy_doc.json
}

#SNS publishing policy document
data "aws_iam_policy_document" "sns_policy_doc" {
  policy_id = "__default"
  statement {
    actions = [
      "SNS:Publish"
    ]
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.rule.arn]
    }
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
    resources = [
      aws_sns_topic.topic.arn
    ]
  }

}
# SQS Publishing policy document
data "aws_iam_policy_document" "sqs_policy_doc" {
  policy_id = "__default"
  statement {
    actions = [
      "SQS:SendMessage"
    ]
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.rule.arn]
    }
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
    resources = [
      aws_sqs_queue.queue.arn
    ]
  }
}

