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
  project_name = "sfn-batch-sample-tf"

}

data "aws_caller_identity" "caller" {}
data "aws_partition" "partition" {}


# This section creates a VPC and related resources for the AWS Batch environment

# VPC to hold all Batch resources
resource "aws_vpc" "vpc" {
  cidr_block = var.vpc_cidr

}

# Create an Internet Gateway
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.vpc.id
}

# Public Route Table
resource "aws_route_table" "public_route" {
  vpc_id = aws_vpc.vpc.id
  route {

    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

}

/* #Attach the IGW to the VPC
resource "aws_internet_gateway_attachment" "gw_attach" {
  internet_gateway_id = aws_internet_gateway.gw.id
  vpc_id              = aws_vpc.vpc.id
} */
#Create a single subnet which allows public IP's
resource "aws_subnet" "subnet" {
  vpc_id                  = aws_vpc.vpc.id
  cidr_block              = var.subnet_cidr
  map_public_ip_on_launch = true
}

# Associate the route table with the subnet
resource "aws_route_table_association" "subnet_rt" {
  subnet_id      = aws_subnet.subnet.id
  route_table_id = aws_route_table.public_route.id
}

#Create a security group for the batch job
resource "aws_security_group" "batch_sg" {
  name        = "${local.project_name}-sg"
  description = "Security group for Batch environment"
  vpc_id      = aws_vpc.vpc.id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]

  }
}

# Create the Role and Policies for the Batch environment
resource "aws_iam_role" "batch_role" {
  name = "${local.project_name}-batch-svc-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "batch.amazonaws.com"
        }
      },
    ]
  })
  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"]
}

#Create the ECS instance role
resource "aws_iam_role" "batch_ecs_role" {
  name = "${local.project_name}-batch-ecs-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })
  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"]
}

# Create the ECS instance profile
resource "aws_iam_instance_profile" "ecs_profile" {
  name = "${local.project_name}-batch-profile"
  role = aws_iam_role.batch_ecs_role.name
}

# Create the AWS Batch Compute Environment
resource "aws_batch_compute_environment" "compute_env" {
  type         = "MANAGED"
  service_role = aws_iam_role.batch_role.arn
  compute_resources {
    max_vcpus     = 64
    min_vcpus     = 0
    desired_vcpus = 2
    type          = "EC2"
    instance_role = aws_iam_instance_profile.ecs_profile.arn
    security_group_ids = [
      aws_security_group.batch_sg.id
    ]
    instance_type = ["optimal"]
    subnets = [
      aws_subnet.subnet.id
    ]
  }
  depends_on = [
    aws_iam_role.batch_ecs_role,
    aws_subnet.subnet,
    aws_security_group.batch_sg,
    aws_iam_role.batch_role
  ]
}

#Create the batch Job Definition
resource "aws_batch_job_definition" "test" {
  name                 = "${local.project_name}-batch-def"
  type                 = "container"
  container_properties = <<CONTAINER_PROPERTIES
  {
  "command":["echo", "Ref::input"],
  "image": "137112412989.dkr.ecr.${var.region}.amazonaws.com/amazonlinux:latest",
  "memory":2000,
  "vcpus":2
}
CONTAINER_PROPERTIES
  retry_strategy {
    attempts = "1"
  }
}

#Create a batch job queue
resource "aws_batch_job_queue" "queue" {
  name     = "${local.project_name}-queue"
  state    = "ENABLED"
  priority = "1"
  compute_environments = [
    aws_batch_compute_environment.compute_env.arn
  ]
}

## Here begins the Step Function creation

#Create a lambda exeuction role
resource "aws_iam_role" "lambda_role" {
  name = "${local.project_name}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]

  })
  managed_policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]
}

#Create the CW Log Group to set retention and delete during cleanup
resource "aws_cloudwatch_log_group" "function_log_group" {
  name              = "/aws/lambda/${local.project_name}-function"
  retention_in_days = "1"
}

#Zip up the lambda code
data "archive_file" "func" {
  type        = "zip"
  source_file = "src/function.py"
  output_path = "${path.module}/files/func.zip"
}

#Create the lambda function which generates the random number
resource "aws_lambda_function" "generate_batch_job_map" {
  function_name    = "${local.project_name}-function"
  filename         = "${path.module}/files/func.zip"
  role             = aws_iam_role.lambda_role.arn
  handler          = "function.handler"
  runtime          = "python3.9"
  source_code_hash = data.archive_file.func.output_base64sha256
}

#Create a role for the step function allowing batch and events actions
resource "aws_iam_role" "batch_job_with_lambda_execution_role" {
  name = "${local.project_name}-sfn-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      },
  ] })
  # Add the necessary policies
  inline_policy {
    name = "BatchJobWithLambdaAccessPolicy"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Action   = ["batch:SubmitJob", "batch:DescribeJobs", "batch:TerminateJob"]
        Effect   = "Allow"
        Resource = "*"
        },
        {
          Action   = ["events:PutTargets", "events:PutRule", "events:DescribeRule"]
          Effect   = "Allow"
          Resource = "arn:${data.aws_partition.partition.id}:events:${var.region}:${data.aws_caller_identity.caller.account_id}:rule/StepFunctionsGetEventsForBatchJobsRule"
        }
      ]
    })
  }
  inline_policy {
    name = "InvokeGenerateBartchJobMapLambdaPolicy"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Action   = ["lambda:InvokeFunction"]
        Effect   = "Allow"
        Resource = [aws_lambda_function.generate_batch_job_map.arn]
      }]
    })
  }
}
# Create the Step Function which submits the batch job 
resource "aws_sfn_state_machine" "batch_job_with_lambda_state_machine" {
  name     = "${local.project_name}-step-function"
  role_arn = aws_iam_role.batch_job_with_lambda_execution_role.arn
  definition = templatefile("${path.module}/statemachine/statemachine.asl.json", {
    GenerateBatchJobArn = aws_lambda_function.generate_batch_job_map.arn,
    partition           = data.aws_partition.partition.id,
    jobQueueArn         = aws_batch_job_queue.queue.arn,
    jobDefinitionArn    = aws_batch_job_definition.test.arn

  })

}

output "state_machine_arn" {
  value = aws_sfn_state_machine.batch_job_with_lambda_state_machine.arn

}

output "state_machine_name" {
  value = aws_sfn_state_machine.batch_job_with_lambda_state_machine.name
}
