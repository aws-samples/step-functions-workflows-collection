# Document Vectorization Pipeline

This workflow demonstrates how to build a serverless document processing pipeline that extracts text from documents, generates vector embeddings using Amazon Bedrock, and stores them in Aurora PostgreSQL with pgvector for similarity search.

Learn more about this workflow from the Step Functions workflows collection: https://serverlessland.com/workflows/document-vectorization-pipeline

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
1. Change directory to the pattern directory:
    ```
    cd document-vectorization-pipeline
    ```
1. From the command line, use AWS SAM to deploy the AWS resources for the workflow as specified in the template.yaml file:
    ```
    ./deploy-with-db-init.sh --region us-east-1
    ```
1. During the prompts:
    * Enter a stack name
    * Enter the desired AWS Region
    * Allow SAM CLI to create IAM roles with the required permissions.

    Once you have run `sam deploy --guided` mode once and saved parameters to a configuration file (samconfig.toml), you can use `sam deploy` in future to use these defaults.

1. Note the outputs from the SAM deployment process. These contain the resource names and/or ARNs which are used for testing.

## How it works

The workflow processes documents uploaded to an S3 bucket through the following steps:

1. **Document Upload**: Documents are uploaded to the S3 bucket's `raw/` prefix
2. **File Type Detection**: The workflow determines the document type (PDF, Word, or text)
3. **Content Extraction**: Appropriate Lambda functions extract text content based on file type
4. **Text Chunking**: Large documents are split into smaller chunks for processing
5. **Parallel Processing**: Multiple chunks are processed simultaneously using Step Functions Map state
6. **Vector Generation**: Each chunk is converted to vector embeddings using Amazon Bedrock
7. **Database Storage**: Vectors are stored in Aurora PostgreSQL with pgvector extension

## Image

![image](./architecture.png)

## Testing

1. Upload a test document to the S3 bucket:
   ```bash
   aws s3 cp test-documents/sample-text.txt s3://[YOUR-BUCKET-NAME]/raw/
   ```

2. Monitor the Step Functions execution in the AWS Console

3. Verify vectors were created in the database:
   ```bash
   ./test-functionality.sh --region us-east-1
   ```

## Cleanup
 
1. Delete the stack
    ```bash
    aws cloudformation delete-stack --stack-name STACK_NAME
    ```
1. Confirm the stack has been deleted
    ```bash
    aws cloudformation list-stacks --query "StackSummaries[?contains(StackName,'STACK_NAME')].StackStatus"
    ```

## Architecture

The workflow uses the following AWS services:

- **Amazon S3**: Document storage and event triggering
- **AWS Step Functions**: Workflow orchestration
- **AWS Lambda**: Document processing and vectorization
- **Amazon Bedrock**: Vector embedding generation
- **Amazon Aurora PostgreSQL**: Vector storage with pgvector
- **Amazon SQS**: Event queuing
- **AWS Secrets Manager**: Database credential management
- **AWS KMS**: Encryption key management

## Key Features

- **Multi-format Support**: Processes PDF, Word (.docx), and text files
- **Scalable Processing**: Parallel chunk processing for large documents
- **Vector Search Ready**: Optimized for similarity search operations
- **Secure**: Encrypted storage and secure credential management
- **Serverless**: Fully managed, pay-per-use architecture

----
Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0