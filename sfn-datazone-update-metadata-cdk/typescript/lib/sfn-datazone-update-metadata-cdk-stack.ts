import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import {
  aws_stepfunctions_tasks as tasks,
  aws_stepfunctions as sfn,
  aws_iam as iam,
  aws_lambda_nodejs as lambda
} from 'aws-cdk-lib';
import * as path from 'path';


export class SfnDataZoneUpdateMetadataCdkStack extends cdk.Stack {

  lambdaRole: iam.Role

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    /**
     * Parameters Configuration DataZone Domain ID and Project ID
     */
    const dataZoneDomainIdParam = new cdk.CfnParameter(this, 'dataZoneDomainId', {
      type: 'String'
    });

    const dataZoneProjectIdParam = new cdk.CfnParameter(this, 'dataZoneProjectId', {
      type: 'String'
    });
    const env = {
      DATAZONE_DOMAIN_ID: dataZoneDomainIdParam.valueAsString,
      DATAZONE_PROJECT_ID: dataZoneProjectIdParam.valueAsString,
    }

    /**
     * Role used for Step function Lambdas
     */
    this.lambdaRole = new iam.Role(this, 'lambdaRole', {
      roleName: 'lambdaDataZoneRole',
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com")
    })
    this.lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: ['datazone:*'],
      resources: ['*'],
      effect: iam.Effect.ALLOW,
    }))

    this.lambdaRole.addManagedPolicy(iam.ManagedPolicy.fromManagedPolicyArn(this, 'managedPolicy', 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'))

    const findAssetFn = this.lambdaFunction('findAssetFn', 'findAssetsHandler', env);
    const updateMetadataFn = this.lambdaFunction('updateMetadataFn', 'updateAssetMetadataFormHandler', env);
    const publishAssetFn = this.lambdaFunction('publishAssetFn', 'publishAssetRevisionHandler', env);

    /**
     * Step Function Constructs & Definition
     */
    const map = new sfn.Map(this, 'Iterate Assets', {
      maxConcurrency: 1,
      itemsPath: sfn.JsonPath.stringAt('$.Payload.assets'),
      parameters: {
        "event": sfn.JsonPath.stringAt('$.Payload.event'),
        "asset": sfn.JsonPath.stringAt('$$.Map.Item.Value'),
      }
    })
    const updateFlow = new tasks.LambdaInvoke(this, 'Update metadata form for Asset', {
      lambdaFunction: updateMetadataFn,
      payloadResponseOnly: true,
    }).next(
      new tasks.LambdaInvoke(this, 'Publish Asset Metadata Revision', {
        lambdaFunction: publishAssetFn
      })
    )

    const startState = new sfn.Pass(this, 'Start State')
      // Run job
      .next(new tasks.LambdaInvoke(this, 'Find assets', {
        lambdaFunction: findAssetFn,
        payload: sfn.TaskInput.fromJsonPathAt('$.Payload'),
      }))
      .next(new sfn.Choice(this, 'Check Assets Found')
        .when(
          sfn.Condition.isPresent('$.Payload.assets'),
          map.iterator(updateFlow)
        )
        .otherwise(new sfn.Fail(this, 'Failed'))
      )

    new sfn.StateMachine(this, 'datazone-update-metadata-sfn', {
      definition: startState,
    });
  }

  /**
   * Lambda utility generator
   * @param id Lambda function id
   * @param handlerName Handler function name in handler.ts
   * @returns 
   */
  private lambdaFunction(id: string, handlerName: string, env: object = {}) {
    return new lambda.NodejsFunction(this, id, {
      entry: path.join(__dirname, 'src', 'handlers.ts'),
      memorySize: 512,
      timeout: cdk.Duration.seconds(60),
      handler: handlerName,
      role: this.lambdaRole,
      environment: {
        ...env
      }
    })
  }
}
