# Word Filtering Script Generator

This workflow generates scripts that filters certain words from video or audio. When you specify the words you wish to filter, [Amazon Transcribe](https://aws.amazon.com/transcribe/) recognizes the word and marks it as `***` in the transcript.
This feature is useful when you want to erase swear words or slang when creating movie subtitles, or when you want to hide certain words.

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
    cd word-filtering-script-generator-cdk/typescript
    ```

1. From the command line, use npm to install dependencies and run the build process.

    ```bash
    npm install
    npm run build
    ```

1. At the bottom of the `app.ts` file, replace the `wordsToFilter` variable with a list of words you would like Amazon Transcribe to filter out of the transcript.

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

1. Based on the words you added to `words_to_filter` variable in the CDK application, an [Amazon Transcribe](https://aws.amazon.com/transcribe/) vocabulary filter will be created. When Transcribe recognizes a word from this filter, it marks it as '***' in the transcript.
1. When a video is uploaded to [Amazon S3](https://aws.amazon.com/s3/) it triggers this workflow.
1. The workflow checks to see if the [Amazon Transcribe](https://aws.amazon.com/transcribe/) vocabulary filter has already been created, otherwise it creates it before proceeding.
1. An [Amazon Transcribe](https://aws.amazon.com/transcribe/) transcription job is created using the `StartTranscriptionJob` API.
1. The workflow then periodically checks to see if the job has completed.
1. Once complete, the job downloads the results of the transcription job and extracts the transcript, ignoring the other transcription metadata.
1. The transcript text is then stored in a separate file on [Amazon S3](https://aws.amazon.com/s3/).

## Testing

1. Deploy the State Machine via CDK.
1. A sample test video is available in the resources folder. Upload the test video to the Amazon S3 bucket created during the deployment step. To find the name of the bucket, navigate to the AWS CloudFormation console. Select the CloudFormation stack created by CDK, `WordFilteringScriptGeneratorPython`. Select the `Outputs` tab and note the `TranscriptMediaBucketOutput` name. A sample video file is available in the `resources` folder.
1. After uploading the video, navigate to the AWS Step Functions console and select the `word-filtering-script-generator-typescript` workflow.
1. The upload event automatically starts the workflow. Observe the execution of the workflow.
1. Once the final transcript text file is stored on S3, the state machine will complete.
1. You can view the transcript by retrieving it from the results S3 bucket. You can find this bucket name from the CloudFormation console. From the `Outputs` tab, note the `TranscriptResultsBucketOutput` name. You can view the text transcribed from the video file including any redaction filtering that may have taken place, replacing the filtered words with '***'.

## Cleanup

To delete the resources created by this template:

1. Delete the stack

    ```bash
    cdk destroy
    ```

1. During the prompts:

    ```bash
    Are you sure you want to delete: WordFilteringScriptGeneratorTypescript (y/n)? Y
    ```

----
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
