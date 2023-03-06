# The "Request response" pattern

When Step Functions calls another service using the Task state, the default pattern is Request Response . With this task orchestration pattern, Step Functions will call the service and then immediately proceed to the next state. The Task state will not wait for the underlying job to complete.

In this module you will run a Task using the Request Response pattern.

When you specify a service in the "Resource" string of your task state, and you only provide the resource, Step Functions will wait for an HTTP response from the service API and then will immediately progress to the next state. Step Functions will not wait for a job to complete. This called the Request Response pattern.

In this sample app we will wait for a specified delay, then we will publish to a SNS topic using the Request Response pattern.

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [AWS CDK Installed](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_install)

## Deployment Instructions

1. If this is your first time using AWS CDK, bootstrap your [environment](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_bootstrap).

    ```bash
    cdk bootstrap aws://{your-aws-account-number}/{your-aws-region}
    ```

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:

    ```bash
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```

1. Change directory to the pattern directory:

    ```bash
    cd request-response-cdk/typescript
    ```

1. From the command line, use npm to install dependencies and run the build process for the Lambda functions.

    ```bash
    npm install
    npm run build
    ```

1. From the command line, use CDK to deploy the AWS resources for the workflow as specified in the ```app.ts``` file:

    ```bash
    cdk deploy
    ```

1. During the prompts:
    * ```Do you wish to deploy these changes (y/n)? Y```

## Image

![image](./resources/statemachine.png)

## Testing

1. Deploy the State Machine via CDK.
2. Subscribe to the SNS Topic to receive the actual message.
3. "Start execution" on this state machine using the following input values:

    ```json
    { "message": "Welcome to re:Invent!", "timer_seconds": 5 }
    ```

4. A successful test results in a successfully published SNS message.

## Cleanup

To delete the resources created by this template:

1. Delete the stack

    ```bash
    cdk destroy
    ```

1. During the prompts:

    ```bash
        Are you sure you want to delete: RequestResponseTypescript (y/n)? Y
    ```

----
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
