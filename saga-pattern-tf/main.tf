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
}

locals {
  project_name = "serverless-saga-pattern"
}

data "aws_caller_identity" "caller" {}
data "aws_partition" "partition" {}


resource "aws_iam_role" "reserve_flight_role" {
  name = "${local.project_name}-reserve-flight-role"
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
}

resource "aws_iam_policy" "reserve_flight_policy" {
  name = "${local.project_name}_reserve_flight_policy"

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/${local.project_name}-Flights"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "lambda_policy" {
  role       = aws_iam_role.reserve_flight_role.name
  policy_arn = aws_iam_policy.reserve_flight_policy.arn
}

data "archive_file" "reserve_flight" {
  type        = "zip"
  source_file = "${path.module}/dist/lambdas/flights/reserveFlight.js"
  output_path = "${path.module}/dist/lambdas/flights/reserveFlight.zip"
}

resource "aws_lambda_function" "reserve_flight_function" {
  function_name    = "${local.project_name}-reserve-flight-fn"
  role             = aws_iam_role.reserve_flight_role.arn
  handler          = "reserveFlight.handler"
  runtime          = "nodejs16.x"
  filename         = "${path.module}/dist/lambdas/flights/reserveFlight.zip"
  source_code_hash = data.archive_file.reserve_flight.output_base64sha256
  environment {
    variables = {
      TABLE_NAME= aws_dynamodb_table.Flights.name
    }
  }
}

resource "aws_iam_role" "reserve_car_rental_role" {
  name = "${local.project_name}-reserve-car-rental-role"
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
}

resource "aws_iam_policy" "reserve_car_rental_policy" {
  name = "${local.project_name}_reserve_car_rental_policy"

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/${local.project_name}-Rentals"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "reserve_car_rental_policy_attachment" {
  role       = aws_iam_role.reserve_car_rental_role.name
  policy_arn = aws_iam_policy.reserve_car_rental_policy.arn
}

data "archive_file" "reserve_car_rental" {
  type        = "zip"
  source_file = "${path.module}/dist/lambdas/rentals/reserveRental.js"
  output_path = "${path.module}/dist/lambdas/rentals/reserveRental.zip"
}

resource "aws_lambda_function" "reserve_car_rental_function" {
  function_name    = "${local.project_name}-reserve-car-rental-fn"
  role             = aws_iam_role.reserve_car_rental_role.arn
  handler          = "reserveRental.handler"
  runtime          = "nodejs16.x"
  filename         = "${path.module}/dist/lambdas/rentals/reserveRental.zip"
  source_code_hash = data.archive_file.reserve_car_rental.output_base64sha256
  environment {
    variables = {
      TABLE_NAME= aws_dynamodb_table.Rentals.name
    }
  }
}

resource "aws_iam_role" "process_payment_role" {
  name = "${local.project_name}-process-payment-role"
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
}


resource "aws_iam_policy" "process_payment_policy" {
  name = "${local.project_name}_process_payment_policy"

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/${local.project_name}-Payments"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "process_payment_policy_attachment" {
  role       = aws_iam_role.process_payment_role.name
  policy_arn = aws_iam_policy.process_payment_policy.arn
}

data "archive_file" "process_payment" {
  type        = "zip"
  source_file = "${path.module}/dist/lambdas/payment/processPayment.js"
  output_path = "${path.module}/dist/lambdas/payment/processPayment.zip"
}

resource "aws_lambda_function" "process_payment_function" {
  function_name    = "${local.project_name}-process-payment-fn"
  role             = aws_iam_role.process_payment_role.arn
  handler          = "processPayment.handler"
  runtime          = "nodejs16.x"
  filename         = "${path.module}/dist/lambdas/payment/processPayment.zip"
  source_code_hash = data.archive_file.process_payment.output_base64sha256
  environment {
    variables = {
      TABLE_NAME= aws_dynamodb_table.Payments.name
    }
  }
}

resource "aws_iam_role" "confirm_flight_role" {
  name = "${local.project_name}-confirm-flight-role"
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
}

resource "aws_iam_policy" "confirm_flight_policy" {
  name = "${local.project_name}-confirm_flight_policy"

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/${local.project_name}-Flights"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "confirm_flight_policy" {
  role       = aws_iam_role.confirm_flight_role.name
  policy_arn = aws_iam_policy.confirm_flight_policy.arn
}

data "archive_file" "confirm_flight" {
  type        = "zip"
  source_file = "${path.module}/dist/lambdas/flights/confirmFlight.js"
  output_path = "${path.module}/dist/lambdas/flights/confirmFlight.zip"
}

resource "aws_lambda_function" "confirm_flight_function" {
  function_name    = "${local.project_name}-confirm-flight-fn"
  role             = aws_iam_role.confirm_flight_role.arn
  handler          = "confirmFlight.handler"
  runtime          = "nodejs16.x"
  filename         = "${path.module}/dist/lambdas/flights/confirmFlight.zip"
  source_code_hash = data.archive_file.confirm_flight.output_base64sha256
  environment {
    variables = {
      TABLE_NAME= aws_dynamodb_table.Flights.name
    }
  }
}

resource "aws_iam_role" "confirm_car_rental_role" {
  name = "${local.project_name}-confirm-car-rental-role"
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
}

resource "aws_iam_policy" "confirm_car_rental_policy" {
  name = "${local.project_name}-confirm_car_rental_policy"

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/${local.project_name}-Rentals"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "confirm_car_rental_attachment" {
  role       = aws_iam_role.confirm_car_rental_role.name
  policy_arn = aws_iam_policy.confirm_car_rental_policy.arn
}

data "archive_file" "confirm_car_rental" {
  type        = "zip"
  source_file = "${path.module}/dist/lambdas/rentals/confirmRental.js"
  output_path = "${path.module}/dist/lambdas/rentals/confirmRental.zip"
}

resource "aws_lambda_function" "confirm_car_rental_function" {
  function_name    = "${local.project_name}-confirm-car-rental-fn"
  role             = aws_iam_role.confirm_car_rental_role.arn
  handler          = "confirmRental.handler"
  runtime          = "nodejs16.x"
  filename         = "${path.module}/dist/lambdas/rentals/confirmRental.zip"
  source_code_hash = data.archive_file.confirm_car_rental.output_base64sha256
  environment {
    variables = {
      TABLE_NAME= aws_dynamodb_table.Rentals.name
    }
  }
}

resource "aws_iam_role" "refund_payment_role" {
  name = "${local.project_name}-refund-payment-role"
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
}

resource "aws_iam_policy" "refund_payment_policy" {
  name = "${local.project_name}-refund_payment_policy"

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:DeleteItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/${local.project_name}-Payments"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "refund_payment_policy_attachment" {
  role       = aws_iam_role.refund_payment_role.name
  policy_arn = aws_iam_policy.refund_payment_policy.arn
}

data "archive_file" "refund_payment" {
  type        = "zip"
  source_file = "${path.module}/dist/lambdas/payment/refundPayment.js"
  output_path = "${path.module}/dist/lambdas/payment/refundPayment.zip"
}

resource "aws_lambda_function" "refund_payment_function" {
  function_name    = "${local.project_name}-refund-payment-fn"
  role             = aws_iam_role.refund_payment_role.arn
  handler          = "refundPayment.handler"
  runtime          = "nodejs16.x"
  filename         = "${path.module}/dist/lambdas/payment/refundPayment.zip"
  source_code_hash = data.archive_file.refund_payment.output_base64sha256
  environment {
    variables = {
      TABLE_NAME= aws_dynamodb_table.Payments.name
    }
  }
}

resource "aws_iam_role" "cancel_car_reservation_role" {
  name = "${local.project_name}-cancel-car-reservation-role"
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
}

resource "aws_iam_policy" "cancel_car_reservation_policy" {
  name = "${local.project_name}-cancel_car_reservation_policy"

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:DeleteItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/${local.project_name}-Rentals"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "cancel_car_reservation_policy_attachment" {
  role       = aws_iam_role.cancel_car_reservation_role.name
  policy_arn = aws_iam_policy.cancel_car_reservation_policy.arn
}

data "archive_file" "cancel_car_reservation" {
  type        = "zip"
  source_file = "${path.module}/dist/lambdas/rentals/cancelRental.js"
  output_path = "${path.module}/dist/lambdas/rentals/cancelRental.zip"
}

resource "aws_lambda_function" "cancel_car_reservation_function" {
  function_name    = "${local.project_name}-cancel-rental-fn"
  role             = aws_iam_role.cancel_car_reservation_role.arn
  handler          = "cancelRental.handler"
  runtime          = "nodejs16.x"
  filename         = "${path.module}/dist/lambdas/rentals/cancelRental.zip"
  source_code_hash = data.archive_file.cancel_car_reservation.output_base64sha256
  environment {
    variables = {
      TABLE_NAME= aws_dynamodb_table.Rentals.name
    }
  }
}

resource "aws_iam_role" "cancel_flight_role" {
  name = "${local.project_name}-cancel-flight-role"
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
}

resource "aws_iam_policy" "cancel_flight_policy" {
  name = "${local.project_name}-cancel_flight_policy"

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:DeleteItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/${local.project_name}-Flights"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "cancel_flight_policy" {
  role       = aws_iam_role.cancel_flight_role.name
  policy_arn = aws_iam_policy.cancel_flight_policy.arn
}


data "archive_file" "cancel_flight" {
  type        = "zip"
  source_file = "${path.module}/dist/lambdas/flights/cancelFlight.js"
  output_path = "${path.module}/dist/lambdas/flights/cancelFlight.zip"
}

resource "aws_lambda_function" "cancel_flight_function" {
  function_name    = "${local.project_name}-cancel-flight-fn"
  role             = aws_iam_role.cancel_flight_role.arn
  handler          = "cancelFlight.handler"
  runtime          = "nodejs16.x"
  filename         = "${path.module}/dist/lambdas/flights/cancelFlight.zip"
  source_code_hash = data.archive_file.cancel_flight.output_base64sha256
  environment {
    variables = {
      TABLE_NAME= aws_dynamodb_table.Flights.name
    }
  }
}

resource "aws_dynamodb_table" "Flights" {
  name           = "${local.project_name}-Flights"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key = "sk"
  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
}
resource "aws_dynamodb_table" "Rentals" {
  name           = "${local.project_name}-Rentals"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key = "sk"
  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
}
resource "aws_dynamodb_table" "Payments" {
  name           = "${local.project_name}-Payments"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key = "sk"
  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
}
resource "aws_sns_topic" "topic" {
  display_name      = "${local.project_name}-booking-topic"
  name              = "${local.project_name}-booking-topic"
  kms_master_key_id = "alias/aws/sns"
}

resource "aws_sns_topic_subscription" "sms-target" {
  topic_arn = aws_sns_topic.topic.arn
  protocol  = "sms"
  endpoint  = "+11111111111"
}

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
    name = "sfn-exec"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          "Action" : [
            "lambda:Invoke*"
          ],
          "Effect" : "Allow",
          "Resource" : [
            aws_lambda_function.reserve_flight_function.arn,
            aws_lambda_function.reserve_car_rental_function.arn,
            aws_lambda_function.process_payment_function.arn,
            aws_lambda_function.confirm_flight_function.arn,
            aws_lambda_function.confirm_car_rental_function.arn,
            aws_lambda_function.refund_payment_function.arn,
            aws_lambda_function.cancel_flight_function.arn,
            aws_lambda_function.cancel_car_reservation_function.arn,
          ]
      },
      {
        "Action": [
          "SNS:Publish"
        ],
        "Effect": "Allow",
        "Resource": aws_sns_topic.topic.arn
      }
      ]
    })
  }
}

resource "aws_sfn_state_machine" "sample_state_machine" {
  name     = "${local.project_name}-sfn"
  role_arn = aws_iam_role.state_machine_exec_role.arn
  definition = templatefile("${path.module}/statemachine/statemachine.asl.json", {
    reserveFlightFunction =     aws_lambda_function.reserve_flight_function.arn,
    reserveCarRentalFunction =  aws_lambda_function.reserve_car_rental_function.arn,
    processPaymentFunction =    aws_lambda_function.process_payment_function.arn,
    confirmFlightFunction =     aws_lambda_function.confirm_flight_function.arn,
    confirmCarRentalFunction =  aws_lambda_function.confirm_car_rental_function.arn,
    refundPaymentFunction =     aws_lambda_function.refund_payment_function.arn,
    cancelFlightFunction =      aws_lambda_function.cancel_flight_function.arn,
    cancelCarRentalFunction =   aws_lambda_function.cancel_car_reservation_function.arn,
    snsTopicArn =               aws_sns_topic.topic.arn,
    }
  )
}

resource "aws_iam_role" "saga_lambda_role" {
  name = "${local.project_name}-saga-lambda-role"
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
}

resource "aws_iam_policy" "saga_lambda_policy" {
  name = "${local.project_name}-topic_saga_lambda_policy"

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "states:StartExecution"
            ],
            "Resource": "arn:aws:states:*:*:stateMachine:${local.project_name}-sfn"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
POLICY
}

resource "aws_iam_role_policy_attachment" "saga_lambda_policy_attachment" {
  role       = aws_iam_role.saga_lambda_role.name
  policy_arn = aws_iam_policy.saga_lambda_policy.arn
}

data "archive_file" "saga_lambda" {
  type        = "zip"
  source_file = "${path.module}/dist/lambdas/sagaLambda.js"
  output_path = "${path.module}/dist/lambdas/sagaLambda.zip"
}

resource "aws_lambda_function" "saga_lambda_function" {
  function_name    = "${local.project_name}-saga-Lambda-fn"
  role             = aws_iam_role.saga_lambda_role.arn
  handler          = "sagaLambda.handler"
  runtime          = "nodejs16.x"
  filename         = "${path.module}/dist/lambdas/sagaLambda.zip"
  source_code_hash = data.archive_file.saga_lambda.output_base64sha256
  environment {
    variables = {
      statemachine_arn= aws_sfn_state_machine.sample_state_machine.arn
    }
  }
}

resource "aws_api_gateway_rest_api" "api_gateway_rest_api" {
  name        = "saga_pattern_apigw_tf"
  description = "API Gateway for Saga Pattern"
}

resource "aws_api_gateway_resource" "api_gateway" {
  rest_api_id = "${aws_api_gateway_rest_api.api_gateway_rest_api.id}"
  parent_id   = "${aws_api_gateway_rest_api.api_gateway_rest_api.root_resource_id}"
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "api_gateway_method" {
  rest_api_id   = "${aws_api_gateway_rest_api.api_gateway_rest_api.id}"
  resource_id   = "${aws_api_gateway_resource.api_gateway.id}"
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "api_gateway_integration" {
  rest_api_id = "${aws_api_gateway_rest_api.api_gateway_rest_api.id}"
  resource_id = "${aws_api_gateway_method.api_gateway_method.resource_id}"
  http_method = "${aws_api_gateway_method.api_gateway_method.http_method}"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "${aws_lambda_function.saga_lambda_function.invoke_arn}"
}

resource "aws_api_gateway_method" "api_gateway_root_method" {
  rest_api_id   = "${aws_api_gateway_rest_api.api_gateway_rest_api.id}"
  resource_id   = "${aws_api_gateway_rest_api.api_gateway_rest_api.root_resource_id}"
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "api_gateway_root_integration" {
  rest_api_id = "${aws_api_gateway_rest_api.api_gateway_rest_api.id}"
  resource_id = "${aws_api_gateway_method.api_gateway_root_method.resource_id}"
  http_method = "${aws_api_gateway_method.api_gateway_root_method.http_method}"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "${aws_lambda_function.saga_lambda_function.invoke_arn}"
}

resource "aws_api_gateway_deployment" "api_gateway_deployment" {
  depends_on = [
    "aws_api_gateway_integration.api_gateway_integration",
    "aws_api_gateway_integration.api_gateway_root_integration",
  ]

  rest_api_id = "${aws_api_gateway_rest_api.api_gateway_rest_api.id}"
  stage_name  = "test"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.saga_lambda_function.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_api_gateway_rest_api.api_gateway_rest_api.execution_arn}/*/*"
}