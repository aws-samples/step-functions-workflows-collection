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

data "aws_caller_identity" "current" {}

data "template_file" "SFDefinitionFile" {
  template = file("${path.module}/statemachines/statemachine.asl.json")
  vars = {
    SF_TableName = aws_dynamodb_table.imagesTable.id
  }
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

# Get the Managed Policy AmazonRekognitionReadOnlyAccess
data "aws_iam_policy" "AmazonRekognitionReadOnlyAccess" {
  arn = "arn:aws:iam::aws:policy/AmazonRekognitionReadOnlyAccess"
}

# Get the Managed Policy AmazonS3ReadOnlyAccess
data "aws_iam_policy" "AmazonS3ReadOnlyAccess" {
  arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
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
        "Action": [
            "dynamodb:*"
        ],
        "Resource": "${aws_dynamodb_table.imagesTable.arn}",
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

# Attach all the IAM policies to the equivalent roles
resource "aws_iam_role_policy_attachment" "StateMachineManagedPolicyAttachment1" {
  role       = aws_iam_role.StateMachineRole.name
  policy_arn = data.aws_iam_policy.AmazonRekognitionReadOnlyAccess.arn
}

# Attach all the IAM policies to the equivalent roles
resource "aws_iam_role_policy_attachment" "StateMachineManagedPolicyAttachment2" {
  role       = aws_iam_role.StateMachineRole.name
  policy_arn = data.aws_iam_policy.AmazonS3ReadOnlyAccess.arn
}

# Create a new DynamoDB table with all attributes and Indexes
resource "aws_dynamodb_table" "imagesTable" {
  name         = "images-data-workflow-pattern-${data.aws_caller_identity.current.account_id}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"
  attribute {
    name = "id"
    type = "S"
  }
}

# Create a new S3 bucket
resource "aws_s3_bucket" "MyS3Bucket" {
  bucket = "data-workflow-pattern-terraform-${data.aws_caller_identity.current.account_id}"
}

# Upload all images to the new S3 bucket
resource "aws_s3_object" "object-building" {
  bucket = aws_s3_bucket.MyS3Bucket.id
  key    = "building.jpg"
  source = "resources/images/building.jpg"
  etag   = filemd5("resources/images/building.jpg")
}

resource "aws_s3_object" "object-desk" {
  bucket = aws_s3_bucket.MyS3Bucket.id
  key    = "desk.jpg"
  source = "resources/images/desk.jpg"
  etag   = filemd5("resources/images/desk.jpg")
}

resource "aws_s3_object" "object-dinos" {
  bucket = aws_s3_bucket.MyS3Bucket.id
  key    = "dinos.jpg"
  source = "resources/images/dinos.jpg"
  etag   = filemd5("resources/images/dinos.jpg")
}

resource "aws_s3_object" "object-office" {
  bucket = aws_s3_bucket.MyS3Bucket.id
  key    = "office.jpg"
  source = "resources/images/office.jpg"
  etag   = filemd5("resources/images/office.jpg")
}

resource "aws_s3_object" "object-stage" {
  bucket = aws_s3_bucket.MyS3Bucket.id
  key    = "stage.jpg"
  source = "resources/images/stage.jpg"
  etag   = filemd5("resources/images/stage.jpg")
}

# Create an Log group for the Step Functions
resource "aws_cloudwatch_log_group" "MySFNLogGroup" {
  name_prefix       = "/aws/vendedlogs/states/StateMachine-terraform-"
  retention_in_days = 60
}

# Create the AWS Step Functions State Machine
resource "aws_sfn_state_machine" "sfn_state_machine" {
  name       = "ProcessImageDataPatternStateMachine-${random_id.randomID.id}"
  role_arn   = aws_iam_role.StateMachineRole.arn
  definition = data.template_file.SFDefinitionFile.rendered
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.MySFNLogGroup.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
}

