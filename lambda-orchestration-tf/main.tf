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
  project_name = "sample-lambda-orchestration"

}

data "aws_caller_identity" "caller" {}
data "aws_partition" "partition" {}

# Create a role for almost all Lambda functions in this project since they only self-generate
# random data. 

resource "aws_iam_role" "function_role" {
  name = "${local.project_name}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action : "sts:AssumeRole"
        Effect : "Allow"
        Sid : ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
}

#Create the check stock price function.
data "archive_file" "check_price" {
  type        = "zip"
  source_file = "src/checkprice.py"
  output_path = "${path.module}/files/check_price.zip"
}

resource "aws_lambda_function" "check_price_function" {
  function_name    = "${local.project_name}-check-stock-fn"
  role             = aws_iam_role.function_role.arn
  handler          = "checkprice.handler"
  runtime          = "python3.9"
  filename         = "${path.module}/files/check_price.zip"
  source_code_hash = data.archive_file.check_price.output_base64sha256
}
# explicitly create the function's log group to set retention and allow auto-cleanup.
resource "aws_cloudwatch_log_group" "check_price_function_log" {
  retention_in_days = 1
  name              = "/aws/lambda/${aws_lambda_function.check_price_function.function_name}"
}

#Create the buy/sell recommendation function.
data "archive_file" "buy-sell-recommend" {
  type        = "zip"
  source_file = "src/buy-sell-recommend.py"
  output_path = "${path.module}/files/buy-sell-recommend.zip"
}

resource "aws_lambda_function" "buy-sell-recommend_function" {
  function_name    = "${local.project_name}-buy-sell-recommend"
  role             = aws_iam_role.function_role.arn
  handler          = "buy-sell-recommend.handler"
  runtime          = "python3.9"
  filename         = "${path.module}/files/buy-sell-recommend.zip"
  source_code_hash = data.archive_file.buy-sell-recommend.output_base64sha256
}
# explicitly create the function's log group to set retention and allow auto-cleanup.
resource "aws_cloudwatch_log_group" "buy-sell-recommend_function_log" {
  retention_in_days = 1
  name              = "/aws/lambda/${aws_lambda_function.buy-sell-recommend_function.function_name}"
}

#Create the buy/sell  function.
data "archive_file" "buy-sell" {
  type        = "zip"
  source_file = "src/buy-sell.py"
  output_path = "${path.module}/files/buy-sell.zip"
}

# Create a role for the buy/sell approval function since it needs different permissions from the rest of 
# the functions in this project

resource "aws_iam_role" "buy_sell_fn_role" {
  name = "${local.project_name}-buy-sell-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action : "sts:AssumeRole"
        Effect : "Allow"
        Sid : ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
  inline_policy {
    #allow receiving sqs messages
    name = "sqs-rw"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          "Action" : [
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes"
          ],
          "Effect" : "Allow",
          "Resource" : [
            aws_sqs_queue.request_approval_queue.arn

          ]
      },
      {
        "Action":["states:SendTask*"],
        "Effect":"Allow",
        "Resource" :[aws_sfn_state_machine.sample_state_machine.arn]
      }
      
      ]
    })
  }
  
}
# This function accepts the event from the approval SQS queue and signals the Step Function to proceed
resource "aws_lambda_function" "buy_sell_function" {
  function_name    = "${local.project_name}-buy-sell"
  role             = aws_iam_role.buy_sell_fn_role.arn
  handler          = "buy-sell.handler"
  runtime          = "python3.9"
  filename         = "${path.module}/files/buy-sell.zip"
  source_code_hash = data.archive_file.buy-sell.output_base64sha256
}
# explicitly create the function's log group to set retention and allow auto-cleanup.
resource "aws_cloudwatch_log_group" "buy_sell_function_log" {
  retention_in_days = 1
  name              = "/aws/lambda/${aws_lambda_function.buy_sell_function.function_name}"
}

#Create the buy  function.
data "archive_file" "buy" {
  type        = "zip"
  source_file = "src/buy.py"
  output_path = "${path.module}/files/buy.zip"
}

resource "aws_lambda_function" "buy_function" {
  function_name    = "${local.project_name}-buy"
  role             = aws_iam_role.function_role.arn
  handler          = "buy.handler"
  runtime          = "python3.9"
  filename         = "${path.module}/files/buy.zip"
  source_code_hash = data.archive_file.buy.output_base64sha256
}
# explicitly create the function's log group to set retention and allow auto-cleanup.
resource "aws_cloudwatch_log_group" "buy_function_log" {
  retention_in_days = 1
  name              = "/aws/lambda/${aws_lambda_function.buy_function.function_name}"
}

#Create the sell  function.
data "archive_file" "sell" {
  type        = "zip"
  source_file = "src/sell.py"
  output_path = "${path.module}/files/sell.zip"
}

resource "aws_lambda_function" "sell_function" {
  function_name    = "${local.project_name}-sell"
  role             = aws_iam_role.function_role.arn
  handler          = "sell.handler"
  runtime          = "python3.9"
  filename         = "${path.module}/files/sell.zip"
  source_code_hash = data.archive_file.sell.output_base64sha256
}
# explicitly create the function's log group to set retention and allow auto-cleanup.
resource "aws_cloudwatch_log_group" "sell_function_log" {
  retention_in_days = 1
  name              = "/aws/lambda/${aws_lambda_function.sell_function.function_name}"
}

# SQS Queue for requesting human approval
resource "aws_sqs_queue" "request_approval_queue" {
  name                       = "${local.project_name}-approvals"
  visibility_timeout_seconds = 180
  kms_master_key_id          = "alias/aws/sqs"
}

# Create the SQS -> Lambda event source for automated approval 
resource "aws_lambda_event_source_mapping" "approval_event" {
  event_source_arn = aws_sqs_queue.request_approval_queue.arn
  function_name    = aws_lambda_function.buy_sell_function.arn
}

#SNS Topic for reporting trade transaction result
resource "aws_sns_topic" "alert_topic" {
  display_name      = "Buy-Sell-Results"
  name              = "${local.project_name}-Results"
  kms_master_key_id = "alias/aws/sns"
}

# State Machine's execution role
resource "aws_iam_role" "state_machine_exec_role" {
  name = "${local.project_name}-sfn-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action : "sts:AssumeRole"
        Effect : "Allow"
        Sid : ""
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
  inline_policy {
    name = "lambda-exec"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          "Action" : [
            "lambda:Invoke*"
          ],
          "Effect" : "Allow",
          "Resource" : [
            aws_lambda_function.check_price_function.arn,
            aws_lambda_function.buy-sell-recommend_function.arn,
            aws_lambda_function.buy_function.arn,
            aws_lambda_function.sell_function.arn

          ]
      }]
    })
  }
  inline_policy {
    name = "sqs-write"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          "Action" : [
            "sqs:SendMessage"
            
          ],
          "Effect" : "Allow",
          "Resource" : [aws_sqs_queue.request_approval_queue.arn]
        }
      ]
    })
  }
  inline_policy {
    name = "sns-publish"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          "Action" : [
            "sns:Publish"
          ],
          "Effect" : "Allow",
          "Resource" : [aws_sns_topic.alert_topic.arn]
        }
      ]
    })
  }
}

# Create the state machine to orchestrate the lambda functions
resource "aws_sfn_state_machine" "sample_state_machine" {
  name     = "${local.project_name}-sfn"
  role_arn = aws_iam_role.state_machine_exec_role.arn
  definition = templatefile("${path.module}/statemachine/statemachine.asl.json", {
    checkPriceFnArn = aws_lambda_function.check_price_function.arn,
    BuySellFnArn    = aws_lambda_function.buy-sell-recommend_function.arn,
    queueUrl        = aws_sqs_queue.request_approval_queue.url,
    buyFnArn        = aws_lambda_function.buy_function.arn,
    sellFnArn       = aws_lambda_function.sell_function.arn,
    topic           = aws_sns_topic.alert_topic.arn

    }
  )
}


# Output the State Machine Name and ARN, and the SNS Topic Name for easy reference
output "state_machine_arn" {
  description = "ARN of sample state machine"
  value = aws_sfn_state_machine.sample_state_machine.arn 
  
}

output "state_machine_name" {
  description = "Name of the sample state machine"
  value = aws_sfn_state_machine.sample_state_machine.name
}

output "topic_name" {
  description = "Name of SNS topic where result is published"
  value = aws_sns_topic.alert_topic.name
  
}