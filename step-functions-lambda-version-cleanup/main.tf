data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  lambda_cleanup_sm_definition = templatefile("${path.module}/statemachine/statemachine.asl.json", {
    sort_functions_fn_name = module.sort_functions_fn.lambda_function_name,
    filter_prefix = var.lambda_function_filter_prefix
  })
}

#--------------------------------------------------
#----------  State machine lambda cleanup
#--------------------------------------------------
module "lambda_cleanup_sfn" {
  source  = "terraform-aws-modules/step-functions/aws"
  version = "~> 4.1.1"

  name       = "lambda-cleanup-sfn"
  definition = local.lambda_cleanup_sm_definition

  service_integrations = {
    xray = {
      xray = true
    }

    lambda = {
      lambda = [
        module.sort_functions_fn.lambda_function_arn
      ]
    }
  }

  type = "STANDARD"

  logging_configuration = {
    include_execution_data = true
    level                  = "ALL"
  }

  cloudwatch_log_group_name              = "/aws/vendedlogs/states/lambda-cleanup-sfn"
  cloudwatch_log_group_retention_in_days = 14

  attach_policy_statements = true
  policy_statements = {
    lambda = {
      effect    = "Allow"
      actions   = ["lambda:ListFunctions"]
      resources = ["*"]
    },
    lambda_specific = {
      effect    = "Allow"
      actions   = ["lambda:DeleteFunction",  "lambda:ListVersionsByFunction"]
      resources = ["arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.lambda_function_filter_prefix}*"]
    }
  }

  tags = {
    Role = "management"
  }
}

# --------------------------------------------------
# ----------  AWS Lambda: sort_functions_fn
# --------------------------------------------------
module "sort_functions_fn" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 6.5.0"

  function_name = "sort-functions"
  handler       = "main.lambda_handler"
  runtime       = "python3.12"
  architectures = ["x86_64"]
  publish       = true

  timeout               = 15 
  memory_size           = 512
  tracing_mode          = "Active"
  attach_tracing_policy = true

  reserved_concurrent_executions = 1
  maximum_retry_attempts         = 2

  create_package         = true 
  source_path = "./lambda"

  cloudwatch_logs_retention_in_days = 14
}

# The code below shows an example of an EventBridge Scheduler which could be used
# to trigger the state machine regularly based on a schedule.

# --------------------------------------------------
# ----------  EventBridge Scheduler Schedule 
# --------------------------------------------------
resource "aws_scheduler_schedule" "lambda_cleanup_state_machine_eb_schedule" {
  name       = "lambda-cleanup-state-machine-eb-schedule"
  group_name = "default"

  description = "Start lambda cleanup state machine"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 3 1 * ? *)"
  schedule_expression_timezone = "Europe/Berlin"

  target {
    arn      = module.lambda_cleanup_sfn.state_machine_arn
    role_arn = aws_iam_role.lambda_cleanup_state_machine_eb_schedule_role.arn
  }
}

## --------------------------------------------------
## ----------  IAM Role for the EventBridge Scheduler Schedule
## --------------------------------------------------
resource "aws_iam_role" "lambda_cleanup_state_machine_eb_schedule_role" {
  name = "lambda-cleanup-state-machine-eb-schedule-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "scheduler.amazonaws.com"
        },
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = "${data.aws_caller_identity.current.account_id}"
          }
        }
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_cleanup_state_machine_eb_schedule_policy" {
  name = "lambda-cleanup-state-machine-eb-schedule-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "states:StartExecution",
        ]
        Effect   = "Allow"
        Resource = "${module.lambda_cleanup_sfn.state_machine_arn}"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_cleanup_state_machine_eb_schedule_attachment" {
  role       = aws_iam_role.lambda_cleanup_state_machine_eb_schedule_role.name
  policy_arn = aws_iam_policy.lambda_cleanup_state_machine_eb_schedule_policy.arn
}

