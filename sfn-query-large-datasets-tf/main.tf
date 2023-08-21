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
  project_name = "query-large-datasets"

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

resource "aws_s3_bucket" "s3_query_large_datasets" {
  bucket = "stepfunctions-query-large-datasets-${random_string.random.result}"
  force_destroy = true
}


resource "aws_sns_topic" "athena_updates" {
  name = "athena-updates-topic"
  kms_master_key_id = "alias/aws/sns"
}

resource "time_sleep" "wait_20_seconds" {
  create_duration = "20s"
}

resource "aws_glue_crawler" "start_athena_crawler" {
  name = "query_large_datasets_crawler-${random_string.random.result}"
  role = aws_iam_role.glue_crawler_role.arn
  database_name = aws_glue_catalog_database.query_large_datasets_db.name

  configuration = jsonencode(
    {
      Grouping = {
        TableGroupingPolicy = "CombineCompatibleSchemas"
      }
      CrawlerOutput = {
        Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
      }
      Version = 1
    }
  )

  s3_target {
    path = "s3://aws-glue-datasets-us-east-1/examples/githubarchive/month/data/"
  }
  depends_on = [time_sleep.wait_20_seconds]
}

resource "aws_glue_catalog_database" "query_large_datasets_db" {
  name = "query_large_datasets_db_${random_string.random.result}"
}


resource "aws_athena_workgroup" "workgroup_start_athena" {
  name  = "log-${random_string.random.result}"
  state = "ENABLED"
  force_destroy = true

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.s3_query_large_datasets.bucket}/result/"
    }
  }
}


resource "aws_iam_role" "state_machine_role" {
  name = "query-large-datasets-${random_string.random.result}"

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
                aws_glue_catalog_database.query_large_datasets_db.arn
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
                "glue:BatchDeletePartition",
                "glue:StartCrawler",
                "glue:GetCrawler"
            ],
            "Resource": [
              "arn:aws:glue:us-east-1:${data.aws_caller_identity.caller.account_id}:catalog",
              "arn:aws:glue:us-east-1:${data.aws_caller_identity.caller.account_id}:database/*",
              "arn:aws:glue:us-east-1:${data.aws_caller_identity.caller.account_id}:table/*/*",
              "arn:aws:glue:us-east-1:${data.aws_caller_identity.caller.account_id}:crawler/*"
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
    aws_athena_workgroup     = aws_athena_workgroup.workgroup_start_athena.name,
    query_large_datasets_db  =  aws_glue_catalog_database.query_large_datasets_db.name
    topic_athena_updates           = aws_sns_topic.athena_updates.arn,
    glue_crawler_name        = aws_glue_crawler.start_athena_crawler.name,

  })
}

output "aws_sfn_state_machine" {
  value = aws_sfn_state_machine.sfn_athena.name
}

output "bucket_domain_name" {
  value = aws_s3_bucket.s3_query_large_datasets.bucket_domain_name
}

output "aws_glue_crawler" {
  value = aws_glue_crawler.start_athena_crawler.name
}