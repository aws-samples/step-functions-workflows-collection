# Concurrency Controller - A Workflow that uses DynamoDB to implement a semaphore
This application demonstrates how to implement control concurrency in your distributed system. This helps you avoid overloading limited resources in your serverless data processing pipeline or reduce availability risk by controlling velocity in your IT automation workflows.  
With this sample application, you implement a distributed semaphore using [AWS Step Functions](https://aws.amazon.com/step-functions/) and [Amazon DynamoDB](https://aws.amazon.com/dynamodb/) to control concurrent invocations of a function in [AWS Lambda](https://aws.amazon.com/lambda/).

For more workflows check https://serverlessland.com/workflows

**Important:** this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli?in=terraform/aws-get-started) installed

## How it works

The template creates a workflow to get you started in implementing control concurrency in your distributed system.

![statemachine](./statemachines/stepfunctions.png)

All provisioned resources will have a name prefix set to `CC` by default. It can be changed by supplying the variable `NamePrefix` value to Terraform. The default region is `us-east-1`, it can also be changed using the variable `region`. The default Semaphore lock name is `MySemaphore`, it can be changed using the variable `LockName`

**Note:** Variables can be supplied in different options, check the [Terraform documentation](https://developer.hashicorp.com/terraform/language/values/variables) for more details.

## Deployment Instructions

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
1. Change directory to the pattern directory:
    ```
    cd step-functions-workflows-collection/app-control-concurrency-with-dynamodb-tf
    ```
1. From the command line, initialize Terraform to download and install the providers defined in the configuration:
    ```
    terraform init
    ```
1. From the command line, apply the configuration in the main.tf file:
    ```
    terraform apply
    ```
1. During the prompts:
    * Enter yes
1. Note the outputs from the deployment process. These contain the resource names and/or ARNs which are used for testing.

## Testing

1. Go to the [AWS Step Functions Console](https://us-east-1.console.aws.amazon.com/states/home) and find the State Machine from the Terraform Output. It should be named \<NamePrefix\>-Test-Run100Executions
    
1. Run the State Machine with any valid input. It will start 100 executions of the workflow that will control concurrency to 5 executions using semaphores.

1. The Lambda function will simulate random failures as part of the workflow to simulate real life scenarios. In those cases the locks will be automatically cleared by the State Machine `CleanFromIncomplete` to prevent deadlocks.

## Cleanup
1. Change directory to the pattern directory:
    ```
    cd step-functions-workflows-collection/app-control-concurrency-with-dynamodb-tf
    ```
1. Delete all created resources
    ```bash
    terraform destroy
    ```
1. During the prompts:
    * Enter yes
1. Confirm all created resources has been deleted
    ```bash
    terraform show
    ```
----
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
