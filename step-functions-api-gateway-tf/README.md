# AWS API Gateway with Step Functions

This workflow demonstrates how to use Step Functions to make a call to an API in AWS API Gateway then check if the call was successful or not. Deploying this sample project will create an AWS Step Functions state machine, an API in AWS API Gateway, required IAM roles and Cloudwatch logs.

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [Terraform Installed](https://www.terraform.io/downloads)

## Deployment Instructions

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
1. Change directory to the pattern directory:
    ```
    cd step-functions-api-gateway-cdk-typescript
    ```
1. If needed, update the variable ```region``` in ```variables.tf``` to the region of your choice.  The default is ```us-east-1```.

1. From the command line, use Terraform to deploy the AWS resources for the workflow as specified in the main.tf file:
    ```
    terraform init
    terraform apply
    ```

1. During the prompts:
    * ```Do you wish to deploy these changes (y/n)? Y ```

1. Note the outputs from the cdk deployment process. The State Machine Name and ARN are outputted for testing.

## How it works

The first step of this workflow makes an API call to the Pet Store API in your AWS account to add a new pet. The next step checks the status returned from the call. If successful, the next step submits a get request to the API to fetch the pet details. If unsuccesful, the step functions goes to fail state and ends. This pattern uses AWS hosted mock APIs to show how to implement this architecture.

## Image

![image](step-functions-api-gateway-tf/resources/statemachine.png)

## Testing

Manually trigger the workflow via the Console or the AWS CLI.  The state machine ARN can be found as the ```StateMachineArn``` output and the state machine name can be found as ```StateMachineName``` in the output.

To trigger the workflow in the console, navigate to Step Functions and then click the step function name from the list of State Machines.  In the Executions panel, click Start Execution.  Click Start Execution again in the popup. Provide the follow sample input :

  {
    "id": 1,
    "type": "dog",
    "price": 249.99
  }

Once the step function completes, inspect the output of the ```Pet was Added Successfully? ``` state.  The output will look similiar to this, but your ```input``` value may be different.
    
{
    {
    "id": 1,
    "type": "dog",
    "price": 249.99
  }
  "message" : "Success"
}
    
Next, inspect the Input of the ```Retrieve the Pet``` state. This shows the result of passing the prior state's output to the input of the next state.  Your input will match the output from the prior state and the output will display the pet you added:
    
   {
    "id": 1,
    "type": "dog",
    "price": 249.99
  }
    

1. Delete the stack
    ```bash
    terraform destroy
    ```
1. Answer ```yes``` to the following prompt:
    
    ```
    Do you really want to destroy all resources?
    Terraform will destroy all your managed infrastructure, as shown above.
    There is no undo. Only 'yes' will be accepted to confirm.

    Enter a value: yes
    ```

----
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
