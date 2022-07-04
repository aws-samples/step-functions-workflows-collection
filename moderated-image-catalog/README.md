# Moderated Image Catalog

This workflow implements a moderated image cataloging pipeline. It includes content moderation, automated tagging, parallel image processing and automated notifications. The workflow relies exclusively on [AWS SDK service integrations](https://docs.aws.amazon.com/step-functions/latest/dg/supported-services-awssdk.html) and contains no custom Lambda code that needs to be maintained.

Learn more about this workflow at Step Functions workflows collection: [Moderated Image Catalog](https://serverlessland.com/workflows/moderated-image-catalog)

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

- [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
- [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [AWS Serverless Application Model](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) (AWS SAM) installed

## Deployment Instructions

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
   ```
   git clone https://github.com/aws-samples/step-functions-workflows-collection
   ```
1. Change directory to the pattern directory:
   ```
   cd moderated-image-catalog
   ```
1. From the command line, use AWS SAM to deploy the AWS resources for the workflow as specified in the template.yaml file:
   ```
   sam deploy --guided
   ```
1. During the prompts:

   - Enter a stack name
   - Enter the desired AWS Region
   - Allow SAM CLI to create IAM roles with the required permissions.
   - Enter an email address that should receive content moderation alerts from the workflow.

   Once you have run `sam deploy --guided` mode once and saved arguments to a configuration file (samconfig.toml), you can use `sam deploy` in future to use these defaults.

1. Note the outputs from the SAM deployment process. These contain the resource names and/or ARNs which are used for testing.

## How it works

![image](./resources/statemachine.png)

1. An image stored in [Amazon S3](https://aws.amazon.com/s3/) is checked for inappropriate content using the [Amazon Rekognition](https://aws.amazon.com/rekognition/) `DetectModerationLabels` API.
2. Based on the result of (1), appropriate images are forwarded to image processing while inappropriate ones trigger an email notification.
3. Appropriate images undergo two processing steps in parallel: the detection of objects and text in the image via Amazon Rekognition’s `DetectLabels` and `DetectText` APIs. The results of both processing steps are saved in an [Amazon DynamoDB](https://aws.amazon.com/dynamodb/) table.
4. An inappropriate image triggers an email notification for manual content moderation via the [Amazon Simple Notification Service (SNS)](https://aws.amazon.com/sns/).

## Testing

1. Upload a test image to the Amazon S3 bucket created during the deployment step. To find the name of the bucket, navigate to the AWS CloudFormation console. Select the CloudFormation stack via the name entered as part of `sam deploy --guided`. Select the `Outputs` tab and note the `IngestionBucket` name.
2. After uploading the image, navigate to the AWS Step Functions console and select the `moderated-image-catalog-workflow` workflow.
3. Select `Start Execution` and input an event as follows:
   ```
   {
       "bucket": "<S3-bucket-name>",
       "key": "<image-name>.jpeg"
   }
   ```
4. Select `Start Execution` and observe the execution of the workflow.
5. Depending on the image selected, it will either be processed and added to the image catalog or a content moderation email will be sent to the email address defined as part of `sam deploy --guided`. Find out more about content considered inappropriate by Amazon Rekognition [here](https://docs.aws.amazon.com/rekognition/latest/dg/moderation.html).

## Cleanup

To delete the resources created by this template, use the following command:

```bash
sam delete
```

---

Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
