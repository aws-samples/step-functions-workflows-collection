# sfn-bedrock-describe-assets

This workflow demonstrates how StepFunctions can manage usage of Amazon Bedrock using Claude Sonnet to describe images and generate HTML alternative text for the images. 

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
2. Change directory to the pattern directory:
    ```
    cd sfn-bedrock-describe-assets
    ```
3. From the command line, use AWS CDK to deploy the AWS resources for the workflow:
    ```
    npx cdk deploy
    ```

## How it works

The example creates an Asset bucket with sample images, a destination bucket that will contain the generated HTML files and a Lambda Function that executes API calls against Bedrock.

When the stack is deployed execute the deployed state machine DescribeAssets with the below parameter. This will initialize the workflow and process the two contained images in parallel. The output will then be written as FILENAME.html containing the ALT HTML text.
{
    "Bucket": "DEPLOYED_BUCKETNAME"
}


The workflow has loose concurrency control, it is pre-configured with MaxConcurrency 10.

This integration pattern can be reused with other services and tasks with Step Functions.

 
## Image
Provide an exported .png of the workflow in the `/resources` directory from [Workflow stuio](https://docs.aws.amazon.com/step-functions/latest/dg/workflow-studio.html) and add here.

![image](./resources/stepfunctions_graph.png)


Notes: 
1. When implementing this workflow in production take care that you change the CDK S3 removalPolicy to your desired settings by removing the below blocks.

```
removalPolicy: cdk.RemovalPolicy.DESTROY,
autoDeleteObjects: true,
```
2. The 'Wait for Textract Callback Token' state implements a 1800 second timeout for processing of Documents

## Cleanup

From the pattern directory, run
 
1. Delete the stack
    ```bash
    npx cdk destroy
    ```

----
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
