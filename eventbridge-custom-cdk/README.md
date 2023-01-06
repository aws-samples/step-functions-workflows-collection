# Event Bridge Custom Event

This workflow demonstrates how to use Step Functions to send a custom event to an EventBridge bus.  The bus contains a rule matching the emitted event. The targets (SNS and SQS) will subsequently process the emitted event.

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
    cd eventbridge-custom-cdk
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



## How it works

1. A new EventBridge bus is created with a single rule forwarding events to a lambda function, an SNS Topic, and a SQS Queue.
1. Manually trigger the Step Function to place a test event on a custom event bus.
1. Each target will receive a copy of the event and process it.

## Image

![image](./resources/statemachine.png)

## Testing

1.  Deploy the State Machine via CDK. 
1.  Trigger the State Machine via the console or CLI.  No input is necessary.
1.  A successful test results in a visible SQS Item, a successful Lambda Execution, and a successfully published SNS message.  

## Cleanup
 
1. Delete the stack
    ```bash
    cdk destroy
    ```
1. During the prompts:
    ```bash
        Are you sure you want to delete: EventbridgeCustomCdkStack (y/n)? Y
    ```
    

----
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
