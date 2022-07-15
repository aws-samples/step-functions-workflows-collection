# Idempotent Workflows

This workflow shows how idempotency can be implemented with StepFunctions. Idempotent workflows always return the same result
when given the same input. In this example, the actual workflow steps are skipped if the workflow has already been executed
with the same payload previously and the previous results are retrieved from DynamoDB and returned as the workflow result instead.
The workflow also implements the concurrency controller pattern which prohibits multiple instances of the workflow to
run concurrently.

Learn more about this workflow at Step Functions workflows collection: https://serverlessland.com/workflows/idempotent-workflow

Important: this application uses various AWS services and there are costs associated with these services after the Free Tier usage - please see the [AWS Pricing page](https://aws.amazon.com/pricing/) for details. You are responsible for any AWS costs incurred. No warranty is implied in this example.

**Important**: The workflow uses DynamoDB to store the results of the actual workflow steps. Therefore, the maximum
size of the results must not exceed ~399 KB (400 KB is maximum but the workflow stores some metadata too).

## Requirements

* [Create an AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html) if you do not already have one and log in. The IAM user that you use must have sufficient permissions to make necessary AWS service calls and manage AWS resources.
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed and configured
* [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) installed
* [AWS CDK](https://docs.aws.amazon.com/en_en/cdk/v2/guide/getting_started.html#getting_started_install) installed

## Deployment Instructions

1. Create a new directory, navigate to that directory in a terminal and clone the GitHub repository:
    ``` 
    git clone https://github.com/aws-samples/step-functions-workflows-collection
    ```
2. Change directory to the pattern directory:
    ```
    cd idempotent-workflow
    ```
3. From the command line, use AWS CDK to deploy the AWS resources for the workflow:
    ```
    npx cdk deploy
    ```

## How it works

The workflow tracks the workflow execution and status in a DynamoDB table. When the workflow starts,
an idempotency key is calculated based on the input event (customizable) and stored in the database as a semaphore
together with a status of `IN_PROGRESS`. 

If storing the key was successful, the workflow runs the actual workflow
steps and records the result in the database with a status of `SUCCESS` (or `FAILED` in case of an error).

If acquiring the semaphore was not successful (i.e. the workflow successfully executed previously or another execution is
running concurrently and thus the status is `IN_PROGRESS`) the workflow retrieves the idempotency record from the database.
When the status is `SUCCESS` and there is a result the result is returned as output of the workflow. If the status is `IN_PROGRESS`
the workflow continues to query the database every 10 seconds until the status changes to either `SUCCESS` and it
continues as described above, or `FAILED`, in which case the workflow tries to acquire the semaphore again.

## Image
![image](./resources/statemachine.png)

## Testing

Start the workflow with some test event, e.g.
```json
{
   "top": "level",
   "nested": {
      "key1": "value1",
      "key2": "value2"
   }
} 
```

The workflow should successfully acquire the lock and execute the right side of the workflow (the parallel state). In
this example, as the last step within the parallel state, a Lambda function is invoked which randomly fails to demonstrate
failure handling. If the Lambda did not fail, the entire workflow should succeed and the result should be the following.
```json
{
  "step1": {
    "result": "Output of step 1"
  },
  "step2": {
    "result": "Output of step 2"
  },
  "step3": {
    "result": "Output of step 3"
  },
  "step4": {
    "result": "Output of step 4"
  },
  "randomFailureFunc": "All good"
}
```

In the DynamoDB table which has been deployed you should find an item with a long hash value as id, an `executionstatus` of
`SUCCESS` and above JSON serialized as string into `executionresult`. The table also holds some info about the execution
which created the item such as execution id and start time. It furthermore uses the `ttl` attribute to auto-expire items
after 24 hours by default.

Now try running the workflow again with the same input as before. This time acquiring the semaphore should fail and the
left side of the workflow should run, which takes the previous result out of the database.

In case the Lambda function failed, the error should have been recorded in the database and the workflow completed with the
"Failure" state. If you try to run the workflow again with the same input it should again successfully acquire the semaphore
and run the right side of the workflow.

You may have to run the workflow a couple of times until the failure lambda succeeds or fails, respectively.

By default the workflow uses the entire input event to calculate the idempotency key. You can customize on which values
the key should be calculated by passing in a JMESPath expression as part of the event. For example
```json
{
   "top": "level",
   "nested": {
      "key1": "value1",
      "key2": "value2"
   },
   "idempotencyKeyJmespath": "[nested.key1, nested.key2]"
} 
```
uses the values of the two nested attributes to calculate the key.


## Cleanup

From the pattern directory, run
 
1. Delete the stack
    ```bash
    npx cdk destroy
    ```

## Usage in your own code

The workflow is provided as a CDK L3 construct (in [idempotent-workflow.ts](lib/idempotent-workflow.ts). You provide your workflow steps as input to the construct as shown in
[idempotent-stepfunctions-workflow-stack.ts](lib/idempotent-stepfunctions-workflow-stack.ts):

```typescript
 new IdempotentWorkflow(this, "IdempotentStepfunctionsWorkflow", {
   workflowSteps: myWorkFlowSteps,
 });
```

**Note**: It is important that all the results from your steps you want to keep in the final result are stored
under the `$.results` key, otherwise the workflow will not be able to extract them properly. You can achieve this
by configuring the `resultPath` property of the steps as shown below
```typescript
new sfn.Pass(this, "Here", {
   parameters: {
     result: "Output of step 1",
   },
   resultPath: "$.results.step1",
 })
```


The construct allows you to configure the TTL and whether it's an StepFunctions Standard or Express workflow. You
can also pass in an existing DynamoDB table to be used for storing idempotency records, or provide your own Lambda
function to calculate the idempotency key.

```typescript
export interface IdempotentWorkflowProps {
  idempotencyHashFunction?: lambda.IFunction;
  idempotencyTable?: ddb.ITable;
  workflowSteps: sfn.IChainable & sfn.INextable;
  express?: boolean,
  ttlMinutes?: number
}
```

If you pass in a custom Lambda function, the function must return a JSON with the following structure where the original
payload is wrapped under an attribute `payload` and the idempotency config under `idempotencyConfig`.
```json
{
   "payload": {
      "top": "level",
      "nested": {
         "key1": "value1",
         "key2": "value2"
      }
   },
   "idempotencyConfig": {
      "idempotencyKey": "6f0fe801ccb08276382f09e4eab91ec8ac8ca5bfe4542952c9d9c9bc77793183",
      "ttl": "1657720121"
   }
}
```

----
Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

SPDX-License-Identifier: MIT-0
