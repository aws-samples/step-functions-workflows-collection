locals {
  orchestrator_state_machine_name = "orchestrate-continous-running-glue-workflow"
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.11"
    }
  }
  required_version = ">= 1.3.0"
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_iam_policy_document" "orchestrate_continous_running_glue_workflow_assume_role_policy" {
  statement {
    actions = [
      "sts:AssumeRole"
    ]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "orchestrate_continous_running_glue_workflow_policy" {
  statement {
    sid = "GetGlueWorkFlowRun"
    actions = [
      "glue:GetWorkflowRun"
    ]
    resources = [
      "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:workflow/*"
    ]
  }

  statement {
    sid = "StartGlueWorkFlowRun"
    actions = [
      "glue:StartWorkflowRun"
    ]
    resources = [
      "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:workflow/*"
    ]
  }

  statement {
    sid = "StartStateExecution"
    actions = [
      "states:StartExecution"
    ]
    resources = [
      "arn:aws:states:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stateMachine:${local.orchestrator_state_machine_name}"
    ]
  }
}


resource "aws_iam_role" "orchestrate_continous_running_glue_workflow_role" {
  name               = "orchestrate-continous-running-glue-workflow-role"
  assume_role_policy = data.aws_iam_policy_document.orchestrate_continous_running_glue_workflow_assume_role_policy.json
}

resource "aws_iam_policy" "orchestrate_continous_running_glue_workflow_policy" {
  name   = "orchestrate-continous-running-glue-workflow-policy"
  policy = data.aws_iam_policy_document.orchestrate_continous_running_glue_workflow_policy.json
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  policy_arn = aws_iam_policy.orchestrate_continous_running_glue_workflow_policy.arn
  role       = aws_iam_role.orchestrate_continous_running_glue_workflow_role.name
}

resource "aws_sfn_state_machine" "orchestrate_continous_running_glue_workflow" {
  name     = local.orchestrator_state_machine_name
  role_arn = aws_iam_role.orchestrate_continous_running_glue_workflow_role.arn

  definition = templatefile("${path.module}/statemachine/statemachine.asl.json", {
    state_machine_arn = "arn:aws:states:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stateMachine:${local.orchestrator_state_machine_name}"
  })
}
