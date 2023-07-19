terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.8"
    }
    random = {
      source = "hashicorp/random"
      version = "3.5.1"
    }
    template = {
      source = "hashicorp/template"
      version = "2.2.0"
    }
  }

  required_version = ">= 1.4.0"
}

provider "aws" {
  region  = var.region
}

data "aws_caller_identity" "current" {}

data "template_file" "sf_definition_file" {
  template = file("${path.module}/statemachine/statemachine.asl.json")
  vars = {
    SF_TableName = aws_dynamodb_table.expenses_table.id
  }
}

# Random string generator
resource "random_id" "randomID" {
  byte_length = 8
}

# Create an IAM role for the Step Functions state machine
resource "aws_iam_role" "sf_role" {
  assume_role_policy = <<EOD
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
EOD
}

# Create an IAM policy for the Step Function
resource "aws_iam_policy" "sf_policy" {
  policy = <<EOD
{
  "Version" : "2012-10-17",
  "Statement" : [
    {
      "Sid": "XRayCWLogs",
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
      "Sid": "rekognition",
      "Action": [
        "rekognition:DetectLabels"
      ],
      "Effect": "Allow",
      "Resource": "*"
    },
    {
      "Sid": "textract",
      "Effect": "Allow",
      "Action": [
          "textract:AnalyzeExpense",
          "textract:GetExpenseAnalysis"
      ],
      "Resource": "*"
    },
    {
        "Sid": "DynamodbUpdateItem",
        "Action": [
            "dynamodb:updateItem"
        ],
        "Resource": "${aws_dynamodb_table.expenses_table.arn}",
        "Effect": "Allow"
    }, {
        "Sid": "S3GetObject",
        "Effect": "Allow",
        "Action": [
            "s3:GetObjectAcl",
            "s3:GetObject",
            "s3:GetObjectVersionAcl",
            "s3:GetObjectVersion"
        ],
        "Resource": "arn:aws:s3:::${aws_s3_bucket.expenses_bucket.id}/*"
    }
  ]
}
EOD
}

# Attach all the IAM policies to the equivalent roles
resource "aws_iam_role_policy_attachment" "sf_policy" {
  role       = aws_iam_role.sf_role.name
  policy_arn = aws_iam_policy.sf_policy.arn
}

# Create a new DynamoDB table with all attributes and Indexes
resource "aws_dynamodb_table" "expenses_table" {
  name         = "textract-analyze-expense-tf-${data.aws_caller_identity.current.account_id}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "Id"
  attribute {
    name = "Id"
    type = "S"
  }
}

# Create a new S3 bucket to store receipt images
resource "aws_s3_bucket" "expenses_bucket" {
  bucket = "textract-analyze-expense-tf-${data.aws_caller_identity.current.account_id}"
}

# Enable EventBridge S3 bucket notification
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket      = aws_s3_bucket.expenses_bucket.id
  eventbridge = true
}

# Create an Log group for the Step Functions
resource "aws_cloudwatch_log_group" "sf_log_group" {
  name_prefix       = "/aws/vendedlogs/states/textract-analyze-expense-tf"
  retention_in_days = 60
}

# Create the AWS Step Functions State Machine
resource "aws_sfn_state_machine" "sfn_state_machine" {
  name       = "textract-analyze-expense-tf-${random_id.randomID.id}"
  role_arn   = aws_iam_role.sf_role.arn
  definition = data.template_file.sf_definition_file.rendered
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sf_log_group.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  depends_on = [ aws_s3_bucket.expenses_bucket ]
}

# IAM role for the the event bridge target
resource "aws_iam_role" "eventbridge_trigger_sfn" {
  assume_role_policy = <<EOD
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
          "Service": "events.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOD
}


# IAM policy for the the event bridge target role to start the StepFunction
resource "aws_iam_policy" "sfn_start_execution" {
  policy = <<EOD
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "states:StartExecution"
            ],
            "Resource": [
                "${aws_sfn_state_machine.sfn_state_machine.arn}"
            ]
        }
    ]
}
EOD
}

resource "aws_iam_role_policy_attachment" "eventbridge_trigger_sfn_attachment" {
  role       = aws_iam_role.eventbridge_trigger_sfn.name
  policy_arn = aws_iam_policy.sfn_start_execution.arn
}

resource "aws_cloudwatch_event_rule" "s3_object_created" {
  name        = "textract-analyze-expense-tf-s3-object-created"
  description = "Object created in the s3 bucket"

  event_pattern = jsonencode({
    source: ["aws.s3"],
    detail-type: ["Object Created"],
    detail: {
      bucket: {
        name: [aws_s3_bucket.expenses_bucket.id]
      }
    }
  })
}


resource "aws_cloudwatch_event_target" "start_step_function" {
  target_id = "StartStepFunction"
  arn       = aws_sfn_state_machine.sfn_state_machine.arn
  rule      = aws_cloudwatch_event_rule.s3_object_created.name
  role_arn  = aws_iam_role.eventbridge_trigger_sfn.arn
}
