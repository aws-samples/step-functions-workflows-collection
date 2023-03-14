# Chain Of Responsibility Pattern

This application creates a mock ATM dispenser workflow. It demonstrates the power of Step Functions to orchestrate Lambda functions using the Chain Of Responsibility behavioral design pattern consisting of a state machine that contains a series of tasks (AWS Lambda Functions), simulating an ATM money dispenser. Each task contains logic that handles a particular part of the money dispensing process and then passes on the result to the next processing task. It is also possible to add new processing tasks at the end of this chain.

The application uses several AWS resources, including Step Functions state machines and Lambda functions.

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [AWS CDK Installed](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_install)

## Deployment Instructions

1. If this is your first time using AWS CDK, bootstrap your [environment](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_bootstrap).
    ```
    cdk bootstrap aws://{your-aws-account-number}/{your-aws-region}
    ```

2. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
3. Change directory to the pattern directory:
    ```
    cd chain-of-responsibility-cdk/python
    ```
4. Create a Python virtual environment and install the requirements:
    ```
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install -r requirements.txt
    ```
5. From the command line, use CDK to deploy the AWS resources for the workflow as specified in the ```app.py``` file:
    ```
    cdk deploy
    ```
6. During the prompts:
    * ```Do you wish to deploy these changes (y/n)? Y ```