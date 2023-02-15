# Step function distributed map workflow with CSV file

This workflow is an example application of a step function using distributed map. This distributed map iterates over an CSV file that is stored in an S3 bucket.

A Map state set to Distributed is known as a Distributed Map state. In this mode, the Map state runs each iteration as a child workflow execution, which enables high concurrency of up to 10,000 parallel child workflow executions. Each child workflow execution has its own, separate execution history from that of the parent workflow. More information about [Using Map state in Distributed mode](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-asl-use-map-state-distributed.html).

For more Step Functions workflows check [ServerlessLand Workflows](https://serverlessland.com/workflows)

**Important:** this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli?in=terraform/aws-get-started) installed

## How it works

![statemachine](./statemachines/stepfunctions.png)

1. The state machine will take as an input a CSV file that contains a header and multiple items. For each item, the Map state runs each iteration as a child workflow execution, which enables high concurrency of up to 10,000 parallel child workflow executions.
2. Each of the Map state will add the item to a DynamoDB table. But you can do more complex things in this state machine.
3. The default region is `us-east-1`, it can also be changed using the variable `region`.

**Note:** Variables can be supplied in different options, check the [Terraform documentation](https://developer.hashicorp.com/terraform/language/values/variables) for more details.

## Deployment Instructions

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
1. Change directory to the pattern directory:
    ```
    cd step-functions-workflows-collection/distributed-map-csv-iterator-tf
    ```
1. From the command line, initialize Terraform to download and install the providers defined in the configuration:
    ```
    terraform init
    ```
1. From the command line, apply the configuration in the main.tf file:
    ```
    terraform apply
    ```
1. During the prompts:
    * Enter yes
1. Note the outputs from the deployment process. These contain the resource names and/or ARNs which are used for testing.

## Testing

1. Upload the sample file `metrics.csv` to an S3 bucket of your choice. The file contain the following structure
    ```
    Content,VideoTitle,VideoPublishTime,Views
    1wNb_RMvI9E,Introduction to AWS Lambda,"May 3, 2021",24993
    xIy0KVMOHHw,Introduction to AWS Amplify,"Jun 15, 2021",13587
    Z_GAa9WToMM,Introduction to AWS SAM,"May 17, 2021",9631
    Zvdf_P5pJis,Introduction to AWS Step Functions,"Aug 23, 2021",15657
    ```
2. Testing can be done by directly invoking the Step Functions State Machine:
    1. Go to the AWS [Step Functions Console](https://us-east-1.console.aws.amazon.com/states/home) and find the State Machine from the Terraform Output. It should be named `CSV-MAP-StateMachine-<random_id>`
    2. Select `Start Execution` and use `{"BucketName": "YOUR-BUCKET-NAME HERE","FileKey": "PREFIX/metrics.csv"}` as a sample input after modifying it with the bucket name where you uploaded the file and the path of the file in the FileKey.
    3. Observe the State Machine workflow execution and check if it is successful
    4. Go to the [Amazon DynamoDB Console](https://us-east-1.console.aws.amazon.com/dynamodbv2/home#tables) and Select the Explore Items from the menu on the left, then select the DynamoDB Table. It should be named `MetaDataTable-<random-id>`
    5. You will be able to find the table updated with the content in the CSV file.

## Cleanup
1. Change directory to the pattern directory:
    ```
    cd step-functions-workflows-collection/distributed-map-csv-iterator-tf
    ```
1. Delete all created resources
    ```bash
    terraform destroy
    ```
1. During the prompts:
    * Enter yes
1. Confirm all created resources has been deleted
    ```bash
    terraform show
    ```

----
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
