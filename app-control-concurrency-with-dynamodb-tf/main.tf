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
  source_file = "${path.module}/functions/app.py"
  output_path = "${path.module}/LambdaFunction.zip"
}

# Get the Managed Policy AWSLambdaBasicExecutionRole
data "aws_iam_policy" "AWSLambdaBasicExecutionRole" {
  arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
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
        "events:PutRule",
        "events:DescribeRule",
        "events:PutTargets",
        "states:StartExecution",
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
        "Resource": "${aws_dynamodb_table.TableSemaphore.arn}",
        "Effect": "Allow"
    },
    {
        "Action": [
            "lambda:InvokeFunction"
        ],
        "Resource": "*",
        "Effect": "Allow"
    }
  ]
}
POLICY1
}

# Create an IAM policy for the EventBridge to execute Step Functions
resource "aws_iam_policy" "EventBridgePolicy" {
  policy = <<POLICY2
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "states:StartExecution"
            ],
            "Resource": [
                "${module.StateMachineSempaphoreCleanup.StateMachineArn}"
            ]
        }
    ]
}
POLICY2
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

resource "aws_iam_role_policy_attachment" "EventBridgePolicyAttachment" {
  role       = aws_iam_role.EventBridgeRole.name
  policy_arn = aws_iam_policy.EventBridgePolicy.arn
}

module "StateMachineSempaphore" {
  source                   = "./modules/Step-Functions"
  region                   = var.region
  SF_Name                  = "${var.NamePrefix}-ConcurrencyControlledStateMachine"
  SF_Role                  = aws_iam_role.StateMachineRole.arn
  SF_LogGroup              = aws_cloudwatch_log_group.MySFNLogGroup.arn
  SF_definitionFile        = "../../statemachines/dynamodb-semaphore.asl.json"
  SF_TableSemaphore        = "${var.NamePrefix}-locktable"
  SF_LockName              = var.LockName
  SF_ConcurrentAccessLimit = "5"
  SF_LambdaARN             = aws_lambda_function.LambdaDoWorkFunction.arn
}

module "StateMachineSempaphoreCleanup" {
  source            = "./modules/Step-Functions"
  region            = var.region
  SF_Name           = "${var.NamePrefix}-CleanFromIncomplete"
  SF_Role           = aws_iam_role.StateMachineRole.arn
  SF_LogGroup       = aws_cloudwatch_log_group.MySFNLogGroup.arn
  SF_definitionFile = "../../statemachines/dynamodb-semaphore-cleanfromincomplete.asl.json"
  SF_TableSemaphore = "${var.NamePrefix}-locktable"
  SF_LockName       = var.LockName
}

module "StateMachineTestSemaphore" {
  source                   = "./modules/Step-Functions"
  region                   = var.region
  SF_Name                  = "${var.NamePrefix}-Test-Run100Executions"
  SF_Role                  = aws_iam_role.StateMachineRole.arn
  SF_LogGroup              = aws_cloudwatch_log_group.MySFNLogGroup.arn
  SF_definitionFile        = "../../statemachines/test-run-semaphore.asl.json"
  SF_StateMachineSemaphore = module.StateMachineSempaphore.StateMachineArn
}

# Create a new DynamoDB table with all attributes and Indexes
resource "aws_dynamodb_table" "TableSemaphore" {
  name         = "${var.NamePrefix}-locktable"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockName"
  attribute {
    name = "LockName"
    type = "S"
  }
}

# Create the Lambda function with the created Zip file of the source code
resource "aws_lambda_function" "LambdaDoWorkFunction" {
  function_name    = "${var.NamePrefix}-LambdaDoWorkFunction"
  filename         = data.archive_file.LambdaZipFile.output_path
  source_code_hash = filebase64sha256(data.archive_file.LambdaZipFile.output_path)
  role             = aws_iam_role.LambdaRole.arn
  handler          = "app.lambda_handler"
  runtime          = "python3.9"
  timeout          = "60"
}

#Create a new EventBridge Rule to handle failed runs of the StateMachineSempaphore
resource "aws_cloudwatch_event_rule" "StateMachineEventRule" {
  event_pattern = <<PATTERN
{
  "source": ["aws.states"],
  "detail": {
    "stateMachineArn": ["${module.StateMachineSempaphore.StateMachineArn}"],
    "status": ["FAILED", "TIMED_OUT", "ABORTED"]
  }
}
PATTERN
}

#Set the log group as a target for the Eventbridge rule
resource "aws_cloudwatch_event_target" "MyRuleTarget" {
  rule     = aws_cloudwatch_event_rule.StateMachineEventRule.name
  arn      = module.StateMachineSempaphoreCleanup.StateMachineArn
  role_arn = aws_iam_role.EventBridgeRole.arn
}

# Create an Log group for the Step Functions
resource "aws_cloudwatch_log_group" "MySFNLogGroup" {
  name_prefix       = "/aws/vendedlogs/states/${var.NamePrefix}-StateMachine-terraform-"
  retention_in_days = 60
}
