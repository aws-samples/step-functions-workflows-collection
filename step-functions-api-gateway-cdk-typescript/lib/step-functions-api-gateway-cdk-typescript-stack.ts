/*
@author : Swapnil Singh
@date : 12/22/2022
*/
import * as cdk from "aws-cdk-lib";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as iam from "aws-cdk-lib/aws-iam";

import {
  HttpIntegration,
  MockIntegration,
  RequestValidator,
  RestApi,
} from "aws-cdk-lib/aws-apigateway";
import { AuthType } from "aws-cdk-lib/aws-stepfunctions-tasks";
import { Construct } from "constructs";
import { Effect } from "aws-cdk-lib/aws-iam";

// extend the props of the stack by adding the vpc type from the SharedInfraStack
export interface StepFunctionsApiGatewayCdkTypescriptStackProps
  extends cdk.StackProps {
  restApi: apigateway.RestApi;
}

export class StepFunctionsApiGatewayCdkTypescriptStack extends cdk.Stack {
  private restApi: apigateway.RestApi;

  constructor(
    scope: Construct,
    id: string,
    props?: StepFunctionsApiGatewayCdkTypescriptStackProps
  ) {
    super(scope, id, props);

    if (props && props.restApi) this.restApi = props.restApi;

    //Set up step function states basedon the statemachine.asl
    //Failed State
    const jobFailed = new sfn.Fail(this, "Failure");

    //Success State, get the pet information
    const jobComplete = new tasks.CallApiGatewayRestApiEndpoint(
      this,
      "Retrieve all Pet Store Data",
      {
        api: this.restApi,
        stageName: "dev",
        apiPath: "/pets",
        method: tasks.HttpMethod.GET,
        authType: AuthType.NO_AUTH
      }
    );

    // Choice State - Was API call successful or not ?
    const statusCheckState = new sfn.Choice(this, "Pet was Added Successfully?",
   {        outputPath: "$.pet.id"  }
    )
      .when(sfn.Condition.stringEquals("$.message", "success"), jobComplete)
      .otherwise(jobFailed);

    // Make API call from Step Functions to Add a Pet to Pet Store
    const apiTask = new tasks.CallApiGatewayRestApiEndpoint(
      this,
      "Add Pet to Store",
      {
        api: this.restApi,
        stageName: "dev",
        apiPath: "/pets",
        method: tasks.HttpMethod.POST,
        requestBody: sfn.TaskInput.fromJsonPathAt("$"),
        authType: AuthType.NO_AUTH,
        outputPath: "$.ResponseBody"
      }
    );

    //Create state machine and start at StartState
    const simpleStateMachine = new sfn.StateMachine(
      this,
      "StepFunctionWithAPI",
      {
        definition: apiTask.next(statusCheckState),
      }
    );

    //Add policy to allow state machine to access API Gateway, Pet Store API
    simpleStateMachine.addToRolePolicy(
      new iam.PolicyStatement({
        effect: Effect.ALLOW,
        actions: ["execute-api:Invoke"],
        resources: [this.restApi.arnForExecuteApi("*")],
      })
    );

    // Add policy to allow Cloudwatch logging
    simpleStateMachine.role.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName("CloudWatchFullAccess")
    );
  }
}
