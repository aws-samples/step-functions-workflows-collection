# AWS Batch with Lambda

This workflow demonstrates how to use Step Functions to pre-process data with AWS Lambda and then orchestrate an AWS Batch job. Deploying this sample project will create an AWS Step Functions state machine, a Lambda function, and an AWS Batch job.

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [Terraform Installed](https://www.terraform.io/downloads)

## Deployment Instructions

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
1. Change directory to the pattern directory:
    ```
    cd batch-lambda-tf
    ```
1. From the command line, use Terraform to deploy the AWS resources for the workflow as specified in the ```main.tf``` file:
    ```
    terraform init
    terraform apply
    ```
1. Note the outputs from the Terraform deployment process. These contain the resource names and ARNs which are used for testing.

## How it works

The first step of this workflow uses a Lambda function to generate a random number and then passes this number to the next step.  Next, the Submit Batch Job step submits an AWS Batch job with the value passed from the previous step.  The AWS Batch job simply prints the supplied argument.

## Image

![image](./resources/statemachine.png)

## Testing

Manually trigger the workflow via the Console or the AWS CLI.  The state machine ARN can be found as the ```state_machine_arn``` output and the state machine name can be found as ```state_machine_name``` in the output.

To trigger the workflow in the console, navigate to Step Functions and then click the step function name from the list of State Machines.  In the Executions panel, click Start Execution.  Click Start Execution again in the popup.  No additional input is required.

Once the step function completes, inspect the output of the ```Generate batch job input``` state.  The output will look similiar to this, but your ```input``` value may be different.
    

    {
        "Comment": "Insert your JSON here",
        "batch_input": {
        "input": "8"
        }
    }
    
Next, inspect the Input of the ```Submit Batch Job``` state. This shows the result of passing the prior state's output to the input of the next state.  Your input will match the output from the prior state:
    
    
    {
        "Comment": "Insert your JSON here",
        "batch_input": {
            "input": "8"
        }
    }
    

## Cleanup
 
1. Delete the stack
    ```bash
    terraform destroy
    ```
1. During the prompts:
    ```bash
    Do you really want to destroy all resources?
    Terraform will destroy all your managed infrastructure, as shown above.
    There is no undo. Only 'yes' will be accepted to confirm.

    Enter a value: Y
    ```
----
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
