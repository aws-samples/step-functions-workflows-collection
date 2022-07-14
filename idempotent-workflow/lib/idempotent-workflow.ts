import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as ddb from "aws-cdk-lib/aws-dynamodb";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as sfnt from "aws-cdk-lib/aws-stepfunctions-tasks";
import * as lambdapy from "@aws-cdk/aws-lambda-python-alpha";
import { Duration, Stack } from "aws-cdk-lib";

export enum WorkflowStatus {
  IN_PROGRESS = "IN_PROGRESS",
  SUCCEEDED = "SUCCEEDED",
  FAILED = "FAILED",
}

export interface IdempotentWorkflowProps {
  workflowSteps: sfn.IChainable & sfn.INextable;
  idempotencyHashFunction?: lambda.IFunction;
  idempotencyTable?: ddb.ITable;
  express?: boolean;
  ttlMinutes?: number;
}

const IDEMPOTENCY_SETTINGS_JSON_PATH = "$.idempotencyConfig";
const IDEMPOTENCY_KEY_JSON_PATH = `${IDEMPOTENCY_SETTINGS_JSON_PATH}.idempotencyKey`;
const IDEMPOTENCY_TTL_JSON_PATH = `${IDEMPOTENCY_SETTINGS_JSON_PATH}.ttl`;

export class IdempotentWorkflow extends Construct {
  constructor(scope: Construct, id: string, props: IdempotentWorkflowProps) {
    super(scope, id);

    const idempotencyFunc: lambda.IFunction =
      props?.idempotencyHashFunction !== undefined
        ? props.idempotencyHashFunction
        : new lambdapy.PythonFunction(this, "IdempotencyConfig", {
            entry: "lambda/idempotency-config/",
            runtime: lambda.Runtime.PYTHON_3_9,
            architecture: lambda.Architecture.X86_64,
            index: "index.py",
            handler: "lambda_handler",
            timeout: Duration.seconds(10),
            layers: [
              lambdapy.PythonLayerVersion.fromLayerVersionArn(
                this,
                "PowerTools",
                `arn:aws:lambda:${
                  Stack.of(this).region
                }:017000801446:layer:AWSLambdaPowertoolsPython:22`
              ),
            ],
            environment: {
              IDEMPOTENCY_RECORD_TTL_MINUTES:
                props.ttlMinutes !== undefined
                  ? props.ttlMinutes.toFixed(0).toString()
                  : "1440", // 24h
              IDEMPOTENCY_JMESPATH_ATTRIBUTE: "idempotencyKeyJmespath",
            },
          });

    const idempotencyTable: ddb.ITable =
      props?.idempotencyTable !== undefined
        ? props.idempotencyTable
        : new ddb.Table(this, "IdempotencyTable", {
            partitionKey: { name: "id", type: ddb.AttributeType.STRING },
            timeToLiveAttribute: "ttl",
            billingMode: ddb.BillingMode.PAY_PER_REQUEST,
            encryption: ddb.TableEncryption.DEFAULT,
          });

    const createIdempotencyKey = new sfnt.LambdaInvoke(
      this,
      "Create idempotency settings (key and ttl)",
      {
        lambdaFunction: idempotencyFunc,
        payloadResponseOnly: true,
        resultPath: "$",
      }
    ).addRetry({
      errors: [
        "Lambda.ServiceException",
        "Lambda.AWSLambdaException",
        "Lambda.SdkClientException",
        "Lambda.TooManyRequestsException",
      ],
      interval: Duration.seconds(3),
      backoffRate: 2,
      maxAttempts: 10,
    });

    const getItem = new sfnt.DynamoGetItem(
      this,
      "Get idempotency record from DynamoDB",
      {
        key: {
          id: sfnt.DynamoAttributeValue.fromString(
            sfn.JsonPath.stringAt(IDEMPOTENCY_KEY_JSON_PATH)
          ),
        },
        projectionExpression: [
          new sfnt.DynamoProjectionExpression().withAttribute(
            "executionstatus"
          ),
          new sfnt.DynamoProjectionExpression().withAttribute(
            "executionresult"
          ),
        ],

        table: idempotencyTable,
        resultPath: "$.idempotencyTable",
      }
    ).addRetry({
      errors: [
        "DynamoDb.ProvisionedThroughputExceededException",
        "DynamoDb.RequestLimitExceeded",
        "DynamoDb.ThrottlingException",
      ],
      interval: Duration.seconds(3),
      backoffRate: 2,
      maxAttempts: 10,
    });

    const extractPreviousResultFromDynamo = new sfn.Pass(
      this,
      "De-serialize previous results",
      {
        parameters: {
          previous_results: sfn.JsonPath.stringToJson(
            sfn.JsonPath.stringAt("$.idempotencyTable.Item.executionresult.S")
          ),
        },
        outputPath: "$.previous_results",
      }
    );

    const delayAndRetryGet = new sfn.Wait(
      this,
      "Still IN_PROGRESS, wait for 10s",
      {
        time: sfn.WaitTime.duration(Duration.seconds(10)),
      }
    );

    const conditionallyLockItem = new sfnt.CallAwsService(
      this,
      "Create and lock idempotency record",
      {
        service: "dynamodb",
        action: "transactWriteItems",
        parameters: {
          TransactItems: [
            {
              Update: {
                ConditionExpression: "attribute_not_exists(#s) or #s = :failed",
                ExpressionAttributeNames: {
                  "#s": "executionstatus",
                  "#e": "execution",
                  "#st": "starttime",
                  "#ttl": "ttl",
                },
                ExpressionAttributeValues: {
                  ":failed": { S: WorkflowStatus.FAILED },
                  ":inprogress": { S: WorkflowStatus.IN_PROGRESS },
                  ":e": { S: sfn.JsonPath.stringAt("$$.Execution.Id") },
                  ":st": { S: sfn.JsonPath.stringAt("$$.Execution.StartTime") },
                  ":ttl": {
                    N: sfn.JsonPath.stringAt(IDEMPOTENCY_TTL_JSON_PATH),
                  },
                },
                Key: {
                  id: { S: sfn.JsonPath.stringAt(IDEMPOTENCY_KEY_JSON_PATH) },
                },
                UpdateExpression:
                  "set #s = :inprogress, #e = :e, #st = :st, #ttl = :ttl",
                TableName: idempotencyTable.tableName,
              },
            },
          ],
        },
        resultPath: sfn.JsonPath.DISCARD,
        iamResources: [idempotencyTable.tableArn],
      }
    )
      .addRetry({
        errors: [
          "DynamoDb.ProvisionedThroughputExceededException",
          "DynamoDb.RequestLimitExceeded",
          "DynamoDb.ThrottlingException",
        ],
        interval: Duration.seconds(3),
        backoffRate: 2,
        maxAttempts: 10,
      })
      .addCatch(getItem, {
        errors: ["DynamoDb.TransactionCanceledException"],
        resultPath: "$.errors.lockItem",
      });

    const checkForFinishedAndGotResult = new sfn.Choice(
      this,
      "Previous or concurrent execution SUCCEEDED, IN_PROGRESS, or FAILED?"
    )
      .when(
        sfn.Condition.and(
          sfn.Condition.stringEquals(
            "$.idempotencyTable.Item.executionstatus.S",
            WorkflowStatus.SUCCEEDED
          ),
          sfn.Condition.isPresent("$.idempotencyTable.Item.executionresult.S")
        ),
        extractPreviousResultFromDynamo
      )
      .when(
        sfn.Condition.stringEquals(
          "$.idempotencyTable.Item.executionstatus.S",
          WorkflowStatus.FAILED
        ),
        conditionallyLockItem
      )
      .when(
        sfn.Condition.stringEquals(
          "$.idempotencyTable.Item.executionstatus.S",
          WorkflowStatus.IN_PROGRESS
        ),
        delayAndRetryGet
      )
      .otherwise(
        new sfn.Fail(this, "Undefined execution state in idempotency record", {
          error: "UndefinedExecutionState",
          cause:
            "The idempotency records exists but the executionstatus is neither SUCCEEDED, IN_PROGRESS, or FAILED",
        })
      );

    const saveResultToDynamo = new sfnt.DynamoUpdateItem(
      this,
      "Save execution results",
      {
        key: {
          id: sfnt.DynamoAttributeValue.fromString(
            sfn.JsonPath.stringAt(IDEMPOTENCY_KEY_JSON_PATH)
          ),
        },
        expressionAttributeNames: {
          "#s": "executionstatus",
          "#r": "executionresult",
        },
        expressionAttributeValues: {
          ":s": sfnt.DynamoAttributeValue.fromString(WorkflowStatus.SUCCEEDED),
          ":r": sfnt.DynamoAttributeValue.fromString(
            sfn.JsonPath.jsonToString(sfn.JsonPath.objectAt("$.results"))
          ),
        },
        updateExpression: "SET #s = :s, #r = :r",
        table: idempotencyTable,
        resultPath: "$.idempotencyTable.updateResult",
        outputPath: "$.results",
      }
    ).addRetry({
      errors: [
        "DynamoDb.ProvisionedThroughputExceededException",
        "DynamoDb.RequestLimitExceeded",
        "DynamoDb.ThrottlingException",
      ],
      interval: Duration.seconds(3),
      backoffRate: 2,
      maxAttempts: 10,
    });

    const saveFailureToDynamo = new sfnt.DynamoUpdateItem(
      this,
      "Save failure",
      {
        key: {
          id: sfnt.DynamoAttributeValue.fromString(
            sfn.JsonPath.stringAt(IDEMPOTENCY_KEY_JSON_PATH)
          ),
        },
        expressionAttributeNames: {
          "#s": "executionstatus",
          "#r": "executionresult",
        },
        expressionAttributeValues: {
          ":s": sfnt.DynamoAttributeValue.fromString(WorkflowStatus.FAILED),
          ":r": sfnt.DynamoAttributeValue.fromString(
            sfn.JsonPath.jsonToString(
              sfn.JsonPath.objectAt("$.errors.childworkflow")
            )
          ),
        },
        updateExpression: "SET #s = :s, #r = :r",
        table: idempotencyTable,
        resultPath: "$.idempotencyTable.updateErrorResult",
        outputPath: "$.errors.childworkflow",
      }
    ).addRetry({
      errors: [
        "DynamoDb.ProvisionedThroughputExceededException",
        "DynamoDb.RequestLimitExceeded",
        "DynamoDb.ThrottlingException",
      ],
      interval: Duration.seconds(3),
      backoffRate: 2,
      maxAttempts: 10,
    });

    const success = new sfn.Succeed(this, "Success");
    const failure = new sfn.Fail(this, "Failure", {
      cause:
        "The child workflow failed. The full exception is available in DynamoDB",
      error: "ChildWorkflowException",
    });

    // Stitch everything together
    const childworkflow = new sfn.Parallel(this, "Your Workflow", {
      resultSelector: {
        results: sfn.JsonPath.objectAt("$.[0]"),
      },
      outputPath: "$.results",
    })
      .branch(props.workflowSteps)
      .addCatch(saveFailureToDynamo, {
        errors: ["States.ALL"],
        resultPath: "$.errors.childworkflow",
      });
    saveFailureToDynamo.next(failure);

    delayAndRetryGet.next(getItem).next(checkForFinishedAndGotResult);
    extractPreviousResultFromDynamo.next(success);
    const sfn_definition = createIdempotencyKey
      .next(conditionallyLockItem)
      .next(childworkflow)
      .next(saveResultToDynamo)
      .next(success);

    const statemachine = new sfn.StateMachine(this, "Statemachine", {
      definition: sfn_definition,
      stateMachineType: props.express
        ? sfn.StateMachineType.EXPRESS
        : sfn.StateMachineType.STANDARD,
    });

    idempotencyTable.grantReadWriteData(statemachine);
  }
}
