# Text to Speech Converter

This workflow takes text files uploaded to Amazon S3 and uses Amazon Polly to synthesis the text to speech. The audio file is saved to Amazon S3.

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
    cd tts-converter-cdk/typescript
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

## How it works

![yoonseo](https://user-images.githubusercontent.com/61778930/183707915-12770755-261c-40f4-9641-7207bb731f7d.jpg)

1. A text file uploaded to [Amazon S3](https://aws.amazon.com/s3/) sends an event to [Amazon EventBridge](https://aws.amazon.com/eventbridge/).
1. An EventBridge rule is configured to look for events from S3 where a new object is created. This rule triggers the [AWS Step Functions](https://aws.amazon.com/step-functions/) state machine.
1. The state machine retrieves the text from the object and then creates a task to synthesis the text to an audio file using [Amazon Polly](https://aws.amazon.com/polly/)'s `startSpeechSynthesisTask` API. Amazon Polly delivers the audio file to a separate S3 bucket.
1. The state machine periodically checks the task status and upon completion, ends the workflow.

## Testing

1. Deploy the application via CDK.
1. Upload a text file to the Amazon S3 bucket created during the deployment step. To find the name of the bucket, navigate to the AWS CloudFormation console. Select the CloudFormation stack created by CDK, `TtsConverterTypescript`. Select the `Outputs` tab and note the `TtsMediaBucketOutput` name. A sample text file is available in the `resources` folder.
1. After uploading the text file, navigate to the AWS Step Functions console and select the `tts-converter-typescript` workflow.
1. The upload event automatically starts the workflow. Observe the execution of the workflow.
1. Once the Amazon Polly task is completed, the state machine will also complete.
1. Once the state machine ends, the audio file that is created is in the results S3 bucket. You can find this bucket name from the CloudFormation console. From the `Outputs` tab, note the `TtsResultsBucketOutput` name. You can download the audio file and listen to the results.

## Cleanup

To delete the resources created by this template:

1. Delete the stack

    ```bash
    cdk destroy
    ```

1. During the prompts:

    ```bash
        Are you sure you want to delete: TtsConverterTypescript (y/n)? Y
    ```

----
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
