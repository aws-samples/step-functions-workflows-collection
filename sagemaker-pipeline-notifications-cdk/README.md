# SageMaker Pipeline Notifications

## What's here?

Choose your preferred language to work with [CDK](https://aws.amazon.com/cdk/):

* [python/](python/) - uses AWS CDK to build and deploy the infrastructure using Python

* [typescript/](typescript/) - uses AWS CDK to build and deploy the infrastructure using Typescript

See README's in specific language folders for specific requirements and deployment steps.

## What does this workflow do?

This workflow implements a notification system for when an [Amazon SageMaker Pipeline](https://aws.amazon.com/sagemaker/pipelines/) execution fails. For customers with many running pipelines, it becomes challenging to see which ones may have failed. This workflow provides an alert of a failed pipeline execution for further investigation as to why the pipeline failed.

![image](./python/resources/statemachine.png)

## Want more?

Check out more workflows on [ServerlessLand](https://serverlessland.com/workflows)

----
Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
