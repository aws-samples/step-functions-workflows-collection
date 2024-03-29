# Human in the Loop

This pattern allows you to integrate an human review or approval process into your workflows. Each task sends a message to a SNS topic which sends a notification to a human reviewer or approver by email for example. The workflow then waits until the approver completes their review. Depending on the review outcome a different Lambda function can be invoked.

Learn more about this workflow at Step Functions workflows collection: [Human in the Loop](https://serverlessland.com/workflows/human-in-the-loop)

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
    cd human-in-the-loop
    ```
1. From the command line, use AWS SAM to deploy the AWS resources for the workflow as specified in the template.yaml file:
    ```
    sam deploy --guided
    ```
1. During the prompts:
    * Enter a stack name
    * Enter the desired AWS Region
    * Allow SAM CLI to create IAM roles with the required permissions.
    * Enter an email address that should receive the notifications from the workflow.

    Once you have run `sam deploy --guided` mode once and saved arguments to a configuration file (samconfig.toml), you can use `sam deploy` in future to use these defaults.

1. Note the outputs from the SAM deployment process. These contain the resource names and/or ARNs which are used for testing.

## How it works

![image](./resources/statemachine.png)

1. Data that should be reviewed by a human is passed to the workflow. A message is send to a [Amazon Simple Notification Service (SNS)](https://aws.amazon.com/sns/) topic which sends out a notification via Email. The notification contains a [task token](https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html#connect-wait-token) which is automatically generated by AWS Step Functions.
2. After approving or denying, the reviewer calls the `SendTaskSuccess` API and passes the task token as well as the review result. 
3. The result is evaluated by Step Functions and the corresponding AWS Lambda function is invoked.  

## Testing

1. After deployment you receive an email titled `AWS Notification - Subscription Confirmation`. Click on the link in the email to confirm your subscription. This will allow SNS to send you emails.
2. Navigate to the AWS Step Functions console and select the `human-in-the-loop` workflow.
3. Select `Start Execution` and use any valid JSON data as input.
4. Select `Start Execution` and wait until you receive the email from SNS.
5. Copy the task token from the email.
6. Use the AWS CLI to complete the task by calling the `SendTaskSuccess` API. Replace the task token with the value you copied earlier. 
    ```
   aws stepfunctions send-task-success --task-token <YOUR-TASK-TOKEN> --task-output '{"result":true}'
   ```
   Make sure to use that the cli uses the same region as the one you used to deploy your state machine.
5. Observe the task in the Step Functions console. Because response states that the approval was granted, the task transitioned to the `Process Approval` step.
6. If you trigger a new execution and replace `{"result":true}` with `{"result":false}` in step 6, the workflow transitions to `Process Rejection` respectively. 

## Cleanup
 
To delete the resources created by this template, use the following command:

```bash
sam delete
```

----
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
