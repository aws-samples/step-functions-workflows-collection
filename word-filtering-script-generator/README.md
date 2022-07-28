# Word Filtering Script Generator

This workflow generates scripts that erase certain words from video or audio.    
When you type the word you want to filter when you create the stack, the video recognizes the word and marks it as `***` in the script.    
This feature is useful when you want to erase swear words or slang when creating movie subtitles, or when you want to hide certain words.   

Learn more about this workflow at Step Functions workflows collection: https://serverlessland.com/workflows/word-filtering-script-generator

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Deployment Instructions

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
1. Change directory to the pattern directory:
    ```
    cd step-functions-workflows-collection/word-filtering-script-generator
    ```
1. From the command line, use AWS SAM to deploy the AWS resources for the workflow as specified in the template.yaml file:
    ```
    sam deploy --guided
    ```
1. During the prompts:
    * Enter a stack name
    * Enter the desired AWS Region
    * Allow SAM CLI to create IAM roles with the required permissions.
    * Enter a word you want to erase in the script (Default value: 'amazon')

1. Note the outputs from the SAM deployment process. These contain the resource names and/or ARNs which are used for testing.

## How it works

When you type the word you want to filter when you create the stack, the video recognizes the word and marks it as '***' in the script. 
You can play the demo, use the [sample-video.mp4 file](./resources/sample-video.mp4) in [resource folder](./resources/).

1. Deploy stack
2. Upload sample video file to S3 bucket (bucket-filtering-media).
3. Then, stateMachine is auto-deployed in Step Functions Console.
4. When StateMachine is end, you can see filtering-script.txt file in S3 bucket (bucket-filtering-results).

## Image
Provide an exported .png of the workflow in the `/resources` directory from [Workflow stuio](https://docs.aws.amazon.com/step-functions/latest/dg/workflow-studio.html) and add here.
![image](./resources/statemachine.png)

## Testing

When you type the word you want to filter when you create the stack, the video recognizes the word and marks it as '***' in the script. 
You can play the demo, use the [sample-video.mp4 file](./resources/sample-video.mp4) in [resource folder](./resources/).

1. Deploy stack
2. Upload sample video file to S3 bucket (bucket-filtering-media).
3. Then, stateMachine is auto-deployed in Step Functions Console.
4. When StateMachine is end, you can see filtering-script.txt file in S3 bucket (bucket-filtering-results).

## Cleanup
 
1. First, You should delete objects in two S3 bucket. (bucket-filtering-media / bucket-filtering-results).
2. Delete the stack
    ```bash
    aws cloudformation delete-stack --stack-name STACK_NAME
    ```
1. Confirm the stack has been deleted
    ```bash
    aws cloudformation list-stacks --query "StackSummaries[?contains(StackName,'STACK_NAME')].StackStatus"
    ```

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [AWS Serverless Application Model](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) (AWS SAM) installed

----
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
