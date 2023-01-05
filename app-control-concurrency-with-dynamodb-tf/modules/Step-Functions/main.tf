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

data "template_file" "SFDefinitionFile" {
  template = file("${path.module}/${var.SF_definitionFile}")
  vars = {
    SF_LambdaARN             = var.SF_LambdaARN
    SF_TableSemaphore        = var.SF_TableSemaphore
    SF_LockName              = var.SF_LockName
    SF_ConcurrentAccessLimit = var.SF_ConcurrentAccessLimit
    SF_StateMachineSemaphore = var.SF_StateMachineSemaphore
  }
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

resource "aws_sfn_state_machine" "sfn_state_machine" {
  name       = var.SF_Name
  role_arn   = var.SF_Role
  definition = data.template_file.SFDefinitionFile.rendered
  logging_configuration {
    log_destination        = "${var.SF_LogGroup}:*"
    include_execution_data = true
    level                  = "ALL"
  }
}