# Support Notifications

This workflow implements a notification system for when critical or urgent cases are created with [AWS Support](https://aws.amazon.com/premiumsupport/). For customers with many administrators who may be logging support cases, a manager may be interested when business critical or production systems are down. Rather than relying on the administrator to add the manager to the case, this automation sends an email notification via [Amazon SNS](https://aws.amazon.com/sns/) to the manager notifying them of the newly created urgent or critical case. The manager can then choose to login to the AWS Console, review the case and add themselves as an additional contact if they wish to receive further case updates. The workflow relies exclusively on [AWS SDK service integrations](https://docs.aws.amazon.com/step-functions/latest/dg/supported-services-awssdk.html) and contains no custom Lambda code that needs to be maintained.

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [Have an AWS Support Plan](https://aws.amazon.com/premiumsupport/plans/) You must have a Business Level Support Plan or higher for access to the AWS Support API.
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
    cd support-notifications-cdk/typescript
    ```

1. From the command line, use npm to install dependencies and run the build process.

    ```bash
    npm install
    npm run build
    ```

1. At the bottom of the `app.ts` file, replace the `notificationEmail` variable with your own email address.

1. Create a system variable `CDK_DEFAULT_ACCOUNT` set to your AWS account id. You can do this in Linux from the command line, with the following:

    ```bash
    export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    ```

1. From the command line, use CDK to deploy the AWS resources for the workflow as specified in the ```app.ts``` file:

    ```bash
    cdk deploy
    ```

1. During the prompts:

    ```text
    Do you wish to deploy these changes (y/n)? Y
    ```

## How it works

![image](./resources/statemachine.png)

1. When a new support case is created with [AWS Support](https://aws.amazon.com/premiumsupport/), it triggers an [Amazon EventBridge](https://aws.amazon.com/eventbridge/) rule which starts the [AWS Step Functions](https://aws.amazon.com/step-functions/) state machine.
1. The state machine uses the [AWS Support API](https://docs.aws.amazon.com/awssupport/latest/user/about-support-api.html) to get more information about the case using the `DescribeCases` API.
1. A Choice step is used to determine if the severity of the case refers to either a 'Production system down' (urgent) or 'Business-critical system down' (critical) severity level. More detail on severity level can be found in the [documentation](https://docs.aws.amazon.com/awssupport/latest/APIReference/API_SeverityLevel.html#API_SeverityLevel_Contents).
1. If the case matches either 'urgent' or 'critical', then an email notification is sent via the [Amazon SNS](https://aws.amazon.com/sns/) topic.
1. If the case does not match the severity level, the state machine ends.

## Testing

1. Deploy the State Machine via CDK using the instructions above, ensuring that you configure your `notificationEmail` and set the `CDK_DEFAULT_ACCOUNT` system variable.
1. You should receive an email requesting confirmation of your subscription to the Amazon SNS topic. Accept this.
1. Create a new support case. As this creates real cases with AWS Support, please ensure that you craft a subject and body that states that this is purely for testing.
1. After creating the case, if it is of the required severity level, you should receive an email notifying of the new case being created from SNS.

## Cleanup

To delete the resources created by this template:

1. Delete the stack

    ```bash
    cdk destroy
    ```

1. During the prompts:

    ```bash
        Are you sure you want to delete: SupportNotificationsTypescript (y/n)? Y
    ```

---

Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
