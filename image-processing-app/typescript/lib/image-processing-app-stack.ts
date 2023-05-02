import { Stack, StackProps, RemovalPolicy, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import { AttributeType, BillingMode, Table } from "aws-cdk-lib/aws-dynamodb";
import {
  Effect,
  PolicyDocument,
  PolicyStatement,
  Role,
  ServicePrincipal,
} from "aws-cdk-lib/aws-iam";
import { Function, Runtime, Code } from "aws-cdk-lib/aws-lambda";
import * as path from "path";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";

export class ImageProcessingAppStack extends Stack {
  declare submitExecution: Function;
  declare getExecutionStatus: Function;

  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    //Dynamo DB
    const dynamoTable = new Table(this, "ChequeIDs", {
      partitionKey: {
        name: "itemId",
        type: AttributeType.STRING,
      },
      tableName: "ChequeIds-Table",
      timeToLiveAttribute: "expiry",
      removalPolicy: RemovalPolicy.DESTROY, // NOT recommended for production code
      billingMode: BillingMode.PAY_PER_REQUEST,
    });

    // Create an IAM role for lambda functions
    const Cheque_Interface_Role = new Role(this, "Cheque_Interface_Role", {
      roleName: "Cheque_Interface_Role",
      description: "IAM Role for Lambda to access other AWS services",
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        {
          managedPolicyArn:
            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        },
        {
          managedPolicyArn:
            "arn:aws:iam::aws:policy/AWSStepFunctionsFullAccess",
        },
        {
          managedPolicyArn: "arn:aws:iam::aws:policy/AmazonS3FullAccess",
        },
      ],
      inlinePolicies: {
        SSMParameter: new PolicyDocument({
          statements: [
            new PolicyStatement({
              effect: Effect.ALLOW,
              resources: ["*"],
              actions: [
                "ssm:GetParameter",
                "secretsmanager:GetResourcePolicy",
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:ListSecretVersionIds",
                "secretsmanager:ListSecrets",
                "s3:CreateBucket",
                "states:DescribeExecution",
              ],
            }),
          ],
        }),
      },
    });

    const StepFunctionsRole = new Role(this, "Role_StepFunctions", {
      roleName: "Role_StepFunctions",
      description: "Role to be assumed for Step Function operations",
      assumedBy: new ServicePrincipal("states.amazonaws.com"),
      managedPolicies: [
        {
          managedPolicyArn: "arn:aws:iam::aws:policy/AWSLambdaExecute",
        },
        {
          managedPolicyArn:
            "arn:aws:iam::aws:policy/service-role/AWSLambdaRole",
        },
      ],
    });

    const Sfn_CreateBucket = new Function(this, "Sfn_CreateBucket", {
      functionName: "BucketCreation",
      runtime: Runtime.NODEJS_16_X,
      code: Code.fromAsset(path.join(__dirname, "./functions")),
      handler: "sfn-CreateBucket.handler",
      role: Cheque_Interface_Role,
      environment: {
        env: "dev",
        APP_REGION: "us-east-1",
        TABLE: "ChequeIds-Table",
      },
      timeout: Duration.seconds(30),
    });

    const Sfn_ZipImages = new Function(this, "Sfn_ZipImages", {
      functionName: "ZipImages",
      runtime: Runtime.NODEJS_16_X,
      code: Code.fromAsset(path.join(__dirname, "./functions")),
      handler: "sfn-ZipImages.handler",
      role: Cheque_Interface_Role,
      memorySize: 1024,
      timeout: Duration.seconds(30),
    });

    const Sfn_GetChequeIds = new Function(this, "Sfn_GetChequeIds", {
      functionName: "GetChequeIDs",
      runtime: Runtime.NODEJS_16_X,
      code: Code.fromAsset(path.join(__dirname, "./functions")),
      handler: "sfn-GetChequeIds.handler",
      role: Cheque_Interface_Role,
      environment: {
        env: "dev",
        APP_REGION: "us-east-1",
        TABLE: "ChequeIds-Table",
      },
      timeout: Duration.seconds(30),
    });

    const Sfn_GetChequeImages = new Function(this, "Sfn_GetChequeImages", {
      functionName: "GetChequeImages",
      runtime: Runtime.NODEJS_16_X,
      code: Code.fromAsset(path.join(__dirname, "./functions")),
      handler: "sfn-GetCheque-Images.handler",
      role: Cheque_Interface_Role,
      environment: {
        env: "dev",
        APP_REGION: "us-east-1",
        TABLE: "ChequeIds-Table",
      },
      memorySize: 1024,
      timeout: Duration.seconds(30),
    });

    dynamoTable.grantReadWriteData(Sfn_CreateBucket);
    dynamoTable.grantReadWriteData(Sfn_GetChequeIds);
    dynamoTable.grantReadWriteData(Sfn_GetChequeImages);
    dynamoTable.grantReadWriteData(Sfn_ZipImages);

    const CreateBucket_Task = new tasks.LambdaInvoke(this, "Create S3 Bucket", {
      lambdaFunction: Sfn_CreateBucket,
      payload: sfn.TaskInput.fromObject({
        token: sfn.JsonPath.entireContext,
      }),
      resultPath: "$.BucketName",
    });

    const GetChequeIds_Task = new tasks.LambdaInvoke(this, "Get Cheque IDs", {
      lambdaFunction: Sfn_GetChequeIds,
      resultPath: "$.ChequesList",
    });

    const GetChequeImages_Task = new tasks.LambdaInvoke(
      this,
      "Generate Cheque Images",
      {
        lambdaFunction: Sfn_GetChequeImages,
        payload: sfn.TaskInput.fromObject({
          token: sfn.JsonPath.entireContext,
          input: sfn.JsonPath.stringAt("$.id"), // ("$.chequeID"), // ChequeID is passed to Lambda function.
        }),
        resultPath: "$.ChequesImages",
      }
    );

    const map_definition = new sfn.Map(this, "Map State", {
      maxConcurrency: 1, //recommended NOT to go beyond 40
      itemsPath: "$.ChequesList.Payload.cheques",
      resultPath: "$.ChequesImagesList",
    });
    map_definition.iterator(GetChequeImages_Task);

    const ZipImages_Task = new tasks.LambdaInvoke(this, "Generate Zip File", {
      lambdaFunction: Sfn_ZipImages,
      resultPath: "$.ZipFile",
    });

    const definition = CreateBucket_Task.next(GetChequeIds_Task) //.next(getStatus);
      .next(map_definition)
      .next(ZipImages_Task);

    new sfn.StateMachine(this, "StateMachine", {
      definition,
      stateMachineName: "Image_Processing_State_Machine",
      //timeout: Duration.minutes(5),
    });
  }
}
