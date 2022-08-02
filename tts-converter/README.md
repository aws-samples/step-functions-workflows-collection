# TTS Converter

This workflow is for reading text files by voice using Amazon Polly.

Learn more about this workflow at Step Functions workflows collection: https://serverlessland.com/workflows/tts-converter

## Deployment Instructions

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
1. Change directory to the pattern directory:
    ```
    cd step-functions-workflows-collection/tts-converter
    ```
1. From the command line, use AWS SAM to deploy the AWS resources for the workflow as specified in the template.yaml file:
    ```
    sam deploy --guided
    ```
1. During the prompts:
    * Enter a stack name
    * Enter the desired AWS Region
    * Allow SAM CLI to create IAM roles with the required permissions.

## How it works

1. Deploy stack.
2. Upload sample text file to S3 bucket (bucket-tts-media).
3. Then, stateMachine is auto-deployed in Step Functions Console.
4. When StateMachine is end, you can see video file in S3 bucket (bucket-tts-results).

## Image

![image](./resources/statemachine.png)

## Testing


1. Deploy stack.
2. Upload sample text file to S3 bucket (bucket-tts-media).
3. Then, stateMachine is auto-deployed in Step Functions Console.
4. When StateMachine is end, you can see video file in S3 bucket (bucket-tts-results).


## Cleanup
 
1. Delete the stack
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
