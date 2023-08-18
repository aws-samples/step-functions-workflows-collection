# Query large datasets (Amazon Athena, Amazon S3, AWS Glue, Amazon SNS)

**Resources used**  

| Resource Type | Name    |
|------------------|--------------------|
| Athena Workgroup | AthenaWorkgroup    |
| State Machine    | AthenaStateMachine |
| SNS Topic        | SNSTopic           |
| S3 Bucket        | DataBucket         |
| Glue Database    | GlueDatabase       |
| Glue Crawler     | GlueCrawler        |  
  
## Start an Athena query

This workflow demonstrates how to ingest a large data set in Amazon S3 and partition it through AWS Glue Crawlers, then execute Amazon Athena queries against that partition. Deploying this sample project creates an AWS Step Functions state machine, an Amazon S3 Bucket, an AWS Glue crawler, and an Amazon SNS topic.

In this project, the Step Functions state machine invokes an AWS Glue crawler that partitions a large dataset in Amazon S3. Once the AWS Glue crawler returns a success message, the workflow executes Athena queries against that partition. Once query execution is successfully complete, a notification is sent to an Amazon SNS topic.

* An Amazon Athena query
* An AWS Glue crawler
* AWS Lambda Functions
* An Amazon Simple Notification Service topic
* Related AWS Identity and Access Management (IAM) roles

Learn more about this workflow at Step Functions workflows collection: https://docs.aws.amazon.com/step-functions/latest/dg/sample-query-large-datasets.html

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-csharp.html) installed

## Deployment Instructions

1. If this is your first time using AWS CDK, bootstrap your [environment](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_bootstrap).
    ```bash
    export ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
    export AWS_REGION=$(aws configure get region)

    cdk bootstrap aws://$ACCOUNT_ID/$AWS_REGION
    ```

2. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ```bash
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
3. Change directory to the pattern directory:
    ```bash
    cd sfn-query-large-datasets-cdk
    ```
4. Create a Python virtual environment and install the requirements:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install -r requirements.txt
    ```
5. From the command line, use CDK to deploy the AWS resources for the workflow as specified in the ```app.py``` file:
    ```bash
    cdk deploy
    ```
6. During the prompts:  
    ```bash
    Do you wish to deploy these changes (y/n)? Y 
    ```

## How it works

The workflow starts by initializing a state machine, and the first task in the sequence is to ingest a large data set in Amazon S3 and partition it through aws Glue Crawlers.

The Athena query is then initiated and runs until it is completed.

Once the query is completed, the results are obtained and published to the SNS (Simple Notification Service) topic. Amazon SNS is a managed service that allows users to send notifications from the cloud to various subscribers or endpoints, such as email, SMS, or mobile push notifications.

## Image

![image](./resources/query-large-datasets.png)

## Testing

Manually trigger the workflow via the Console or the AWS CLI.  The state machine ARN can be found as the ```state_machine_arn``` CloudFormation output and the state machine name can be found as ```state_machine_name``` in the CloudFormation output.

To trigger the workflow in the console, navigate to Step Functions and then click the step function name from the list of State Machines.  In the Executions panel, click Start Execution.  Click Start Execution again in the popup (default input values can be ignored).

## Cleanup
 
1. Delete the stack
    ```bash
    cdk destroy
    ```
2. During the prompts:
    ```bash
    Are you sure you want to delete: SfnQueryLargeDatasets (y/n)?

    Enter a value: y
    ```

## Additional Security Topics  
For increased security, the cdk stack is extended with [CDK-NAG](https://pypi.org/project/cdk-nag/). This package does identify security and compliance issues in your stack and validates constructs by extending [AWS CDK Aspects](https://docs.aws.amazon.com/cdk/v2/guide/aspects.html). cdk-nag includes several rule sets (NagPacks) to validate your application against. As of this readme post, cdk-nag includes the [AWS Solutions](https://github.com/cdklabs/cdk-nag/blob/main/RULES.md#awssolutions), [HIPAA Security](https://github.com/cdklabs/cdk-nag/blob/main/RULES.md#hipaa-security), [NIST 800-53 rev 4](https://github.com/cdklabs/cdk-nag/blob/main/RULES.md#nist-800-53-rev-4), [NIST 800-53 rev 5](https://github.com/cdklabs/cdk-nag/blob/main/RULES.md#nist-800-53-rev-5), and [PCI DSS 3.2.1](https://github.com/cdklabs/cdk-nag/blob/main/RULES.md#pci-dss-321) NagPacks. You can pick and choose different NagPacks and apply as many as you wish to a given scope.

Check out [this blog post](https://aws.amazon.com/blogs/devops/manage-application-security-and-compliance-with-the-aws-cloud-development-kit-and-cdk-nag/) for a guided overview!

## Want more?

Check out more workflows on [ServerlessLand](https://serverlessland.com/workflows).
  
----

Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0