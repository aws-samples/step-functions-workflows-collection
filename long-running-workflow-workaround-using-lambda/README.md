# Continue Long Running Workflow using Lambda Function

AWS Step Functions is designed to run workflows that have a finite duration and number of steps. Executions have a maximum duration of one year, and a maximum of 25,000 events.

You can also implement a pattern that uses a Lambda function to start a new execution of your state machine to split ongoing work across multiple workflow executions.

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [AWS Serverless Application Model](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) (AWS SAM) installed

## Deployment Instructions

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
1. Change directory to the pattern directory:
    ```
    cd long-running-workflow-workaround-using-lambda
    ```
1. From the command line, use AWS SAM to deploy the AWS resources for the workflow as specified in the template.yaml file:
    ```
    sam deploy --guided
    ```
1. During the prompts:
    * Enter a stack name
    * Enter the desired AWS Region
    * Allow SAM CLI to create IAM roles with the required permissions.

    Once you have run `sam deploy --guided` mode once and saved arguments to a configuration file (samconfig.toml), you can use `sam deploy` in future to use these defaults.

1. Note the outputs from the SAM deployment process. These contain the resource names and/or ARNs which are used for testing.

## How it works

You can create a state machine that uses a Lambda function to start a new execution before the current execution terminates. Using this approach to continue your ongoing work in a new execution enables you to have a state machine that can break large jobs into smaller workflows, or to have a state machine that runs indefinitely. It works in the following way.

- In this step functions workflow we use iterator to count number of executions.
- Once the iterator count reaches threshold, another execution is started.
- Lambda function is used to start a new execution.

## Image
![image](./resources/statemachine.png)

## Modifications needed

1. Before the template is deployed, modify example-workflow.json to set region name and account id.
2. After the modifications are made, follow deployment instructions.

## Start Execution of Workflow
1. You can start execution of State Machine from AWS Console after successful deployment.
2. Use sample_event.txt to pass event while starting execution.

## Cleanup
 
1. Delete the stack
    ```bash
    aws cloudformation delete-stack --stack-name STACK_NAME
    ```
1. Confirm the stack has been deleted
    ```bash
    aws cloudformation list-stacks --query "StackSummaries[?contains(StackName,'STACK_NAME')].StackStatus"
    ```
----
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
