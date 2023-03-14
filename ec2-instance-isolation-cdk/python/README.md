# EC2 Instance Isolation

This is an AWS SAM template for automated security reponse to isolate an EC2 instance. Below is an explanation of how to deploy the template containing the step function state machine.

This example is modeled after the potential security anomaly on an EC2 instance section in the `[AWS Security Incident Response guide](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/welcome.html) under Infrastructure Domain Incidents.

Learn more about this workflow at Step Functions workflows collection: https://serverlessland.com/workflows/ec2-instance-isolation-sam

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

2. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:

    ```bash
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```

3. Change directory to the pattern directory:

    ```bash
    cd ec2-instance-isolation-cdk/python
    ```

4. Create a Python virtual environment and install the requirements:

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install -r requirements.txt
    ```

5. At the bottom of the `app.py` file, replace the `vpcId` variable with your VPC ID.

6. From the command line, use CDK to deploy the AWS resources for the workflow as specified in the ```app.py``` file:

    ```bash
    cdk deploy
    ```

7. During the prompts:

    ```text
    Do you wish to deploy these changes (y/n)? Y
    ```


## How it works

This step function orchestrates the process of isolating an EC2 instance involved in a potential security anomaly.,
Using all native API calls the step function: 
1. Captures the metadata from the Amazon EC2 instance.
2. Protects the Amazon EC2 instance from accidental termination by enabling termination protection for the instance.
3. Isolates the Amazon EC2 instance by switching the VPC Security Group.
4. Detach the Amazon EC2 instance from any AWS Auto Scaling groups. Which will deregister the Amazon EC2 instance from any related Elastic Load Balancing service.
5. Snapshots the Amazon EBS data volumes that are attached to the EC2 instance for preservation and follow-up investigations.
6. Tags the Amazon EC2 instance as quarantined for investigation, and add any pertinent metadata, such as the trouble ticket associated with the investigation.
7. Creates a forensic instance with the EBS volume from the suspected instance and allows ingress to the quarantined instance.

## Image
![image](./resources/statemachine.png)

## Testing

The Step Function can be triggered with the with the instance id of the instance to isolate.
Example:
    ```
    {
        "IsolatedInstanceId": "i-01234567890abc"
    }
    ```