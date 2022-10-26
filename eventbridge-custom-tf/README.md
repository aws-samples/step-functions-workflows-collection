# Event Bridge Custom Event

This workflow demonstrates how to use Step Functions to send a custom event to an EventBridge bus.  The bus contains a rule matching the emitted event. The targets (SNS and SQS) will subsequently process the emitted event.

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
    cd eventbridge-custom-tf
    ```
1. If needed, update the variable ```region``` in ```variables.tf``` to the region of your choice.  The default is ```us-east-1```.
1. From the command line, use Terraform to deploy the AWS resources for the workflow as specified in the main.tf file:
    ```
    terraform init
    terraform apply
    ```
1. During the prompts:
    * Enter 'yes' when prompted to deploy the changes


## How it works

1. A new EventBridge bus is created with a single rule forwarding events to a lambda function, an SNS Topic, and a SQS Queue.
1. Manually trigger the Step Function to place a test event on a custom event bus.
1. Each target will receive a copy of the event and process it.

## Image

![image](./resources/statemachine.png)

## Testing

1.  Deploy the State Machine via Terraform. 
1.  Trigger the State Machine via the console or CLI.  No input is necessary.
1.  A successful test results in a visible SQS Item, a successful Lambda Execution, and a successful SNS message published to the topic.  

## Cleanup
 
1. Delete the stack
    ```bash
    terraform destroy
    ```
    Answer the prompts as follows:
    ```bash
        Do you really want to destroy all resources?
        Terraform will destroy all your managed infrastructure, as shown above.
        There is no undo. Only 'yes' will be accepted to confirm.

        Enter a value: yes
    ```
    
----
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
