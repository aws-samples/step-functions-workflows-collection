# Moderated Image Catalog

This workflow implements a moderated image cataloging pipeline. It includes content moderation, automated tagging, parallel image processing and automated notifications. The workflow relies exclusively on [AWS SDK service integrations](https://docs.aws.amazon.com/step-functions/latest/dg/supported-services-awssdk.html) and contains no custom Lambda code that needs to be maintained.

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
    cd moderated-image-catalog-cdk/typescript
    ```

1. From the command line, use npm to install dependencies and run the build process.

    ```bash
    npm install
    npm run build
    ```

1. At the bottom of the `app.ts` file, replace the `moderator_email` variable with your own email address.

1. From the command line, use CDK to deploy the AWS resources for the workflow as specified in the ```app.ts``` file:

    ```bash
    cdk deploy
    ```

1. During the prompts:
    * ```Do you wish to deploy these changes (y/n)? Y```

## How it works

![image](./resources/statemachine.png)

1. An image stored in [Amazon S3](https://aws.amazon.com/s3/) is checked for inappropriate content using the [Amazon Rekognition](https://aws.amazon.com/rekognition/) `DetectModerationLabels` API.
2. Based on the result of (1), appropriate images are forwarded to image processing while inappropriate ones trigger an email notification.
3. Appropriate images undergo two processing steps in parallel: the detection of objects and text in the image via Amazon Rekognition’s `DetectLabels` and `DetectText` APIs. The results of both processing steps are saved in an [Amazon DynamoDB](https://aws.amazon.com/dynamodb/) table.
4. An inappropriate image triggers an email notification for manual content moderation via the [Amazon Simple Notification Service (SNS)](https://aws.amazon.com/sns/) topic.

## Testing

1. Deploy the State Machine via CDK.
1. Upload a test image to the Amazon S3 bucket created during the deployment step. To find the name of the bucket, navigate to the AWS CloudFormation console. Select the CloudFormation stack created by CDK, `ModeratedImageCatalogTypescript`. Select the `Outputs` tab and note the `IngestionBucketOutput` name.
1. After uploading the image, navigate to the AWS Step Functions console and select the `moderated-image-catalog-workflow-typescript` workflow.
1. Select `Start Execution` and input an event as follows:

   ```json
   {
       "bucket": "<S3-bucket-name>",
       "key": "<image-name>.jpeg"
   }
   ```

1. Select `Start Execution` and observe the execution of the workflow.
1. Depending on the image selected, it will either be processed and added to the image catalog or a content moderation email will be sent to the `moderator_email` address defined in the CDK stack in `app.ts`. Find out more about content considered inappropriate by Amazon Rekognition [here](https://docs.aws.amazon.com/rekognition/latest/dg/moderation.html).

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
