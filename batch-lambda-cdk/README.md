# AWS Batch with Lambda

This workflow demonstrates how to use Step Functions to pre-process data with AWS Lambda and then orchestrate an AWS Batch job. Deploying this sample project will create an AWS Step Functions state machine, a Lambda function, and an AWS Batch job.

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [AWS CDK Installed](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_install)

## Deployment Instructions

1. If this is your first time using AWS CDK, bootstrap your [environment](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_bootstrap).
    ```
    cdk bootstrap aws://{your-aws-account-number}/{your-aws-region}
    ```
1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
1. Change directory to the pattern directory:
    ```
    cd batch-lambda-cdk/batch_lambda_cdk
    ```
1. Create a Python virtual environment and install the requirements:
    ```
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install -r requirements.txt
    ```
1. From the command line, use CDK to deploy the AWS resources for the workflow as specified in the ```app.py``` file:
    ```
    cdk deploy
    ```
1. During the prompts:
    * ```Do you wish to deploy these changes (y/n)? Y ```

1. Note the outputs from the cdk deployment process. The State Machine Name and ARN are outputted for testing.

## How it works

The first step of this workflow uses a Lambda function to generate a random number and then passes this number to the next step.  Next, the Submit Batch Job step submits an AWS Batch job with the value passed from the previous step.  The AWS Batch job simply prints the supplied argument.

## Image

![image](batch_lambda_cdk/resources/statemachine.png)

## Testing

Manually trigger the workflow via the Console or the AWS CLI.  The state machine ARN can be found as the ```StateMachineArn``` output and the state machine name can be found as ```StateMachineName``` in the output.

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
    cdk destroy
    ```
1. During the prompts:
    ```bash
        Are you sure you want to delete: BatchLambdaCdkStack (y/n)? Y
    ```
----
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
