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
  project_name = "start-athena-query"

}

data "aws_caller_identity" "caller" {}
data "aws_partition" "partition" {}

resource "aws_iam_role" "glue_crawler_role" {
  name = "glue-crawler-role-${random_string.random.result}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
  ]
}

resource "random_string" "random" {
  length           = 16
  special          = false
  upper            = false
}

resource "aws_s3_bucket" "s3_start_athena" {
  bucket = "stepfunctions-start-athena-query-${random_string.random.result}"
  force_destroy = true
}

resource "aws_iam_role" "invoke_crawler_function" {
  name = "${local.project_name}-invoke-crawler-lambda-role-${random_string.random.result}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "invoke_crawler_function_policy" {
  name = "invoke_crawler_function_policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "glue:StartCrawler",
          "glue:GetCrawler"
        ],
        Resource = "*",
        Effect = "Allow"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  policy_arn = aws_iam_policy.invoke_crawler_function_policy.arn
  role = aws_iam_role.invoke_crawler_function.name
}


resource "aws_lambda_function" "invoke_crawler_function" {
  function_name    = "${local.project_name}-invoke-crawler-${random_string.random.result}"
  role             = aws_iam_role.invoke_crawler_function.arn
  handler          = "invoke_crawler.lambda_handler"
  runtime          = "python3.9"
  filename         = "${path.module}/invoke_crawler.zip"
  timeout          = 300

  environment {
    variables = {
      ATHENA_CRAWLER = aws_glue_crawler.start_athena_crawler.name
    }
  }
}

data "archive_file" "invoke_crawler_function_code" {
  type        = "zip"
  source_file  = "${path.module}/src/invoke_crawler.py"
  output_path = "invoke_crawler.zip"
}


resource "aws_iam_role" "data_generation_function" {
  name = "${local.project_name}-data-generation-lambda-role-${random_string.random.result}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "data_generation_function_policy" {
  name = "data_generation_function_policy"
  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "s3:PutObject"
            ],
            "Resource": [
              "${aws_s3_bucket.s3_start_athena.arn}/*"
              ],
            "Effect": "Allow"
        }
    ]
  })
  }

resource "aws_iam_role_policy_attachment" "data_generation_function_policy_attachment" {
  policy_arn = aws_iam_policy.data_generation_function_policy.arn
  role = aws_iam_role.data_generation_function.name
}

resource "aws_lambda_function" "data_generation_function" {
  function_name    = "${local.project_name}-data-generation-${random_string.random.result}"
  role             = aws_iam_role.data_generation_function.arn
  handler          = "data_generation.lambda_handler"
  runtime          = "python3.9"
  filename         = "${path.module}/data_generation.zip"
  timeout          = 240

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.s3_start_athena.bucket
    }
  }
}

data "archive_file" "data_generation_function_code" {
  type        = "zip"
  source_file = "${path.module}/src/data_generation.py"
  output_path = "data_generation.zip"
}


resource "aws_sns_topic" "athena_updates" {
  name = "athena-updates-topic"
  kms_master_key_id = "alias/aws/sns"
}

resource "time_sleep" "wait_60_seconds" {
  create_duration = "60s"
}

resource "aws_glue_crawler" "start_athena_crawler" {
  name = "start_athena_query_crawler-${random_string.random.result}"
  role = aws_iam_role.glue_crawler_role.arn
  database_name = aws_glue_catalog_database.start_athena_query_db.name
  s3_target {
    path = "s3://${aws_s3_bucket.s3_start_athena.bucket}"
  }
  depends_on = [time_sleep.wait_60_seconds]
}

resource "aws_glue_catalog_database" "start_athena_query_db" {
  name = "start_athena_query_db_${random_string.random.result}"
}

resource "aws_glue_catalog_table" "aws_glue_catalog_table" {
  name          = "log"
  database_name = aws_glue_catalog_database.start_athena_query_db.name
  table_type = "EXTERNAL_TABLE"
  parameters = {
    "classification" = "csv"
  }
  storage_descriptor {
    location = "s3://${aws_s3_bucket.s3_start_athena.bucket}/log/"
    input_format = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"
    ser_de_info {
      name = "log"
      serialization_library = "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
      parameters = {
        "field.delim" = ","
      }
    }
    columns {
      name = "year"
      type = "bigint"
    }
    columns {
      name = "grade"
      type = "string"
    }
  }
}

resource "aws_athena_workgroup" "workgroup_start_athena" {
  name  = "log-${random_string.random.result}"
  state = "ENABLED"
  force_destroy = true

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.s3_start_athena.bucket}/result/"
    }
  }
}


resource "aws_iam_role" "state_machine_role" {
  name = "start-athena-query-${random_string.random.result}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "state_machine_policy" {
  name = "sfn-start-athena-policy-${random_string.random.result}"

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                aws_lambda_function.data_generation_function.arn,
                aws_lambda_function.invoke_crawler_function.arn
            ],
            "Effect": "Allow"
        },
        {
            "Action": [
                "sns:Publish"
            ],
            "Resource": [
                aws_sns_topic.athena_updates.arn
            ],
            "Effect": "Allow"
        },
        {
            "Action": [
                "athena:getQueryResults",
                "athena:startQueryExecution",
                "athena:stopQueryExecution",
                "athena:getQueryExecution",
                "athena:getDataCatalog"
            ],
            "Resource": [
                aws_athena_workgroup.workgroup_start_athena.arn,
                aws_glue_catalog_database.start_athena_query_db.arn
            ],
            "Effect": "Allow"
        },
        {
            "Action": [
                "s3:GetBucketLocation",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads",
                "s3:ListMultipartUploadParts",
                "s3:AbortMultipartUpload",
                "s3:CreateBucket",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::*",
            "Effect": "Allow"
        },
        {
            "Action": [
                "glue:CreateDatabase",
                "glue:GetDatabase",
                "glue:GetDatabases",
                "glue:UpdateDatabase",
                "glue:DeleteDatabase",
                "glue:CreateTable",
                "glue:UpdateTable",
                "glue:GetTable",
                "glue:GetTables",
                "glue:DeleteTable",
                "glue:BatchDeleteTable",
                "glue:BatchCreatePartition",
                "glue:CreatePartition",
                "glue:UpdatePartition",
                "glue:GetPartition",
                "glue:GetPartitions",
                "glue:BatchGetPartition",
                "glue:DeletePartition",
                "glue:BatchDeletePartition"
            ],
            "Resource": [
              "arn:aws:glue:us-east-1:${data.aws_caller_identity.caller.account_id}:catalog",
              "arn:aws:glue:us-east-1:${data.aws_caller_identity.caller.account_id}:database/*",
              "arn:aws:glue:us-east-1:${data.aws_caller_identity.caller.account_id}:table/*/*"
            ],
            "Effect": "Allow"
        }
    ]
}
   )
}

resource "aws_iam_role_policy_attachment" "state_machine_custom_policy_attachment" {
  policy_arn = aws_iam_policy.state_machine_policy.arn
  role       = aws_iam_role.state_machine_role.id
}

resource "aws_sfn_state_machine" "sfn_athena" {
  name     = "state-machine-start-athena-${random_string.random.result}"
  role_arn = aws_iam_role.state_machine_role.arn
    definition = templatefile("${path.module}/statemachine/statemachine.asl.json", {
    data_generation_function = aws_lambda_function.data_generation_function.arn,
    invoke_crawler_function  = aws_lambda_function.invoke_crawler_function.arn,
    aws_athena_workgroup     = aws_athena_workgroup.workgroup_start_athena.name,
    start_athena_query_db    =  aws_glue_catalog_database.start_athena_query_db.name
    athena_updates           = aws_sns_topic.athena_updates.arn

  })
}


output "aws_sfn_state_machine" {
  value = aws_sfn_state_machine.sfn_athena.name
}

output "invoke_crawler_function" {
  value = aws_lambda_function.invoke_crawler_function.arn
}

output "data_generation_function" {
  value = aws_lambda_function.data_generation_function.arn
}

output "bucket_domain_name" {
  value = aws_s3_bucket.s3_start_athena.bucket_domain_name
}
