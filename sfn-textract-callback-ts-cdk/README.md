# sfn-textract-callback

This workflow shows how the Callback pattern can be applied to the asynchronous Textract StartDocumentTextDetection API call.

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
2. Change directory to the pattern directory:
    ```
    cd sfn-textract-callback-ts-cdk
    ```
3. From the command line, use AWS CDK to deploy the AWS resources for the workflow:
    ```
    npx cdk deploy
    ```

## How it works

The example demonstrates the integration of the StartDocumentDetection Textract API into Step Functions. The Workflow input is an  S3 bucket and object key. The Step Function will begin by processing the object with Textract and then use the Callback method by creating the Textract JobID with its Callback Token onto DynamoDB.

While waiting for a Callback, the pre-configured SNS notification on the StartDocumentDetection Task will notify a Lambda Function once the Textract JobID has completed. The Lambda Function will then resume the Step Function by returning the callback Token. Once this executes succesfully a message will be sent out through SNS. 

This integration pattern can be reused with other services and tasks with Step Functions.

 
## Image
Provide an exported .png of the workflow in the `/resources` directory from [Workflow stuio](https://docs.aws.amazon.com/step-functions/latest/dg/workflow-studio.html) and add here.

![image](./resources/stepfunctions_graph.png)

## Testing

There are two ways to test the Step Functions Workflow.

1. Uploading an S3 Object with text onto the Source Bucket deployed by the CDK deployment
2. Start the workflow with a test event as in the example by below. You must replace the BUCKET_NAME with the source bucket deployed through CDK.
```json
{
  "detail": {
    "bucket": {
        "name": "BUCKET_NAME"
    },
    "object": {
        "key": "cat.pdf"
    }
  }
}
```

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
## Architecture

Some components from the workflow are not rendered through Workflow Studio as they are not Workflow components. They are still required for the solution and the schematic is as follows. 

1. When an object is placed onto the Source Bucket an S3 Object Created Event is sent out to Event Bridge
2. Event Bridge then initiates the Step Function
3. The first step is to initiate the Asynchronous StartDocumentDetection API 
4. The Step Function records the JobID and a CallBack Token on DynamoDB 
5. The Step Functions pauses until Textract completes the Text extraction and it receives a Call Back Token to continue
6. Once Textract has completed it emits an SNS event which notifies the Step Function Callback Handler Lambda Function
7. The Step Function Callback Handler Lambda Function retrieves the Callback Token from DynamoDB by matching the JobID
8. Once retrieved it signals the Step Function to continue 
9. The Step Function emits an SNS signal that it has completed which can be used for further integration

![image](./resources/TextractOverview.drawio.png)

----
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
