# Activity state machine

This application creates a State Machine with Activity state that enables you to implement a worker hosted anywhere. An activity worker can be an application running on EC2 instance/ AWS Lambda or a mobile device application that can make HTTP connection. 

The example workflow runs an activity task state which waits for activity worker running on AWS Lambda. When State Machine workflow reaches activity task state, it pauses in "In progress" status and waits for activity worker to poll for a task. Once the function polls for activity task, the workflow then waits for the time configured in "TimeoutSeconds" to allow worker complete and report success/failure.

For more Step Functions workflows check [ServerlessLand Workflows](https://serverlessland.com/workflows)

**Important:** this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli?in=terraform/aws-get-started) installed

## How it works

![statemachine](./statemachines/stepfunctions.png)

1. When the task state "Step Functions Run Activity" runs the Activity "Activity-<random_id>", the workflow execution pauses for activity worker to poll the task using "GetActivityTask" API call.
2. Once the activity worker(Lambda function) polls for the task, then the workflow waits for "Timeout" seconds, thus allowing worker to return it's success/failure/heartbeat.
3. The workflow execution succeeds only if the activity worker has completed it's execution successfully.

**Note:** Variables can be supplied in different options, check the [Terraform documentation](https://developer.hashicorp.com/terraform/language/values/variables) for more details.

## Deployment Instructions

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
1. Change directory to the pattern directory:
    ```
    cd step-functions-workflows-collection/activity-state-machine-tf
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

1. Go to the AWS [Step Functions Console](https://us-east-1.console.aws.amazon.com/states/home) and find the State Machine from the Terraform Output. It should be named `ActivityStateMachine-<random_id>`
2. Select `Start Execution` and use any valid JSON data as input.
3. As the workflow reaches activity task state, it pauses for worker to poll. Navigate to AWS Lambda console and select `WorkerFunction-<random_id>`.
4. Test the function from console using any valid JSON data as input.
5. Observe the State Machine workflow execution.

## Cleanup
1. Change directory to the pattern directory:
    ```
    cd step-functions-workflows-collection/activity-state-machine-tf
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
