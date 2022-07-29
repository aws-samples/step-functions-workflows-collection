# "Script Generator" Application

In this application, you can generate **Script file** in Video file.

When you upload video file to S3 bucket, state machine will start processing **video to text**.
The script content is extracted from the video and stored as `script.txt` in S3.

Learn more about this workflow at Step Functions workflows collection: *To be Added...*

![image](./resources/statemachine.png)

## How to Deploy
0. First, you should install [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) (Serverless Application Model)

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    
    cd step-functions-workflows-collection/script-generator 
    ```
2. From the command line, use AWS SAM to deploy the AWS resources for the workflow as specified in the template.yaml file:
    ```
    sam deploy --guided
    ```

    *You can set the default value by pressing the enter key continuously. Below is example commands.

    ```bash
    Configuring SAM deploy
    ======================

        Looking for config file [samconfig.toml] :  Not found

        Setting default arguments for 'sam deploy'
        =========================================
        Stack Name [sam-app]: 
        AWS Region [ap-northeast-2]: 
        #Shows you resources changes to be deployed and require a 'Y' to initiate deploy
        Confirm changes before deploy [y/N]: y
        #SAM needs permission to be able to create roles to connect to the resources in your template
        Allow SAM CLI IAM role creation [Y/n]: 
        Save arguments to configuration file [Y/n]: 
        SAM configuration file [samconfig.toml]: 
        SAM configuration environment [default]: 

        Looking for resources needed for deployment:
        Creating the required resources...
    ```

3. When all resources are provisioned, Upload your video file to `transcript-media` bucket in S3.
<img width="964" alt="image" src="https://user-images.githubusercontent.com/61778930/180661643-af55375b-54ce-4ddb-8956-c7fc81e0c3db.png">

4. After that, state machine will be deployed. When deployments are done, you can see `script.txt` file in `transcript-results` S3 bucket.
<img width="892" alt="image" src="https://user-images.githubusercontent.com/61778930/181208277-8c33d6b1-f1c8-42cc-9f06-da3ace305476.png">


## Cleanup
 
1. Delete the stack
    ```bash
    aws cloudformation delete-stack --stack-name STACK_NAME
    ```
1. Confirm the stack has been deleted
    ```bash
    aws cloudformation list-stacks --query "StackSummaries[?contains(StackName,'STACK_NAME')].StackStatus"
    ```


### Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git Installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [AWS Serverless Application Model](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) (AWS SAM) installed

----
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
