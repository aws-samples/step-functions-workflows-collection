import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import {
  aws_s3 as s3,
  aws_s3_deployment as s3Deploy,
  aws_emrserverless as emrSls,
  aws_stepfunctions_tasks as tasks,
  aws_stepfunctions as sfn,
  aws_iam as iam
} from 'aws-cdk-lib';
import * as path from 'path'

export class StepFunctionsEMRServerlessStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    /* S3 bucked containing:
      - input_data/ -> folder with the input CSV data
      - emr_scripts/ -> folder containing the pySpark scripts that emr executes
      - output/ -> folder used by EMR for output (processed parquet file)
    */
    const bucket = new s3.Bucket(this, 'bucket', {
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true
    })
    new s3Deploy.BucketDeployment(this, 'deployment', {
      destinationBucket: bucket,
      sources: [s3Deploy.Source.asset(path.join(__dirname, 'include'))]
    })


    /*
    Create the EMR Application. Configure the application to start when there's a job start request.
    The application automatically stop after a number of minutes(10 in this example) to reduce costs.
    The EMR Serverless cluster can be created with a never-stop mode (for streaming purpose for instance)
    */
    const emrApplication = new emrSls.CfnApplication(this, 'emr_serverless_app', {
      releaseLabel: 'emr-6.9.0',
      type: 'Spark',
      architecture: 'ARM64',
      // Auto start configuration: the application starts when there is a job request
      autoStartConfiguration: {
        enabled: true,
      },
      // Auto stop configuration: the application stops after being idle for N minutes
      autoStopConfiguration: {
        enabled: true,
        idleTimeoutMinutes: 10,
      },
      maximumCapacity: {
        cpu: '64',
        memory: '256',
      },
      name: 'EmrServerless_StepFunction_Example',
    })

    const emrRole = new iam.Role(this, 'emrRole', {
      assumedBy: new iam.ServicePrincipal("emr-serverless.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonS3FullAccess")
      ]
    })


    // EMR API call -> StartJobRun: Start a EMR serverless job using the provided input
    const startTask = new tasks.CallAwsService(this, 'start-job-EMR', {
      service: 'emrserverless',
      action: 'startJobRun',
      parameters: {
        ApplicationId: emrApplication.attrApplicationId,
        ClientToken: sfn.JsonPath.uuid(),
        ExecutionRoleArn: emrRole.roleArn,
        JobDriver: {
          SparkSubmit: {
            EntryPoint:
              `s3://${bucket.bucketName}/emr_scripts/spark_main.py`,
            EntryPointArguments: [
              `s3://${bucket.bucketName}/input_data/BTCGBP.csv`,
              `s3://${bucket.bucketName}/output`
            ],
            SparkSubmitParameters:
              "--conf spark.hadoop.hive.metastore.client.factory.class=com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"
          }
        }
      },
      iamResources: ['*'],
      additionalIamStatements: [
        new iam.PolicyStatement({
          actions: ['emr-serverless:StartJobRun'],
          resources: ['*'],
        }),
        new iam.PolicyStatement({
          actions: ['iam:PassRole'],
          resources: ['*'],
        }),
      ],
      resultPath: sfn.JsonPath.stringAt('$.Job.Input')
    })
    // EMR API call -> GetJobRun: Get the status for a Job run givin a JobRunId
    const checkTask = new tasks.CallAwsService(this, 'get-status-EMR', {
      service: 'emrserverless',
      action: 'getJobRun',
      parameters: {
        ApplicationId: emrApplication.attrApplicationId,
        JobRunId: sfn.JsonPath.stringAt('$.Job.Input.JobRunId')
      },
      iamResources: ['*'],
      additionalIamStatements: [
        new iam.PolicyStatement({
          actions: ['emr-serverless:GetJobRun'],
          resources: ['*'],
        })
      ],
      resultPath: sfn.JsonPath.stringAt('$.Job.Status')
    })

    // Polling interval - the step functions periodically call EMR to obtain the job status
    const intervalInSeconds = 20

    const startState = new sfn.Pass(this, 'StartState')
      // Run job
      .next(startTask)
      // Check job status
      .next(checkTask)
      .next(new sfn.Choice(this, 'check-job-success')
        // If success -> end(completed)
        .when(sfn.Condition.and(
          sfn.Condition.isPresent('$.Job.Status'),
          sfn.Condition.or(
            sfn.Condition.stringEquals('$.Job.Status.JobRun.State', 'SUCCESS'))),
          new sfn.Succeed(this, 'completed'))
        .otherwise(
          // If failed/cancelled -> end(failure)
          new sfn.Choice(this, 'check-job-failure').when(
            sfn.Condition.and(
              sfn.Condition.isPresent('$.Job.Status'),
              sfn.Condition.or(
                sfn.Condition.stringEquals('$.Job.Status.JobRun.State', 'CANCELLED'),
                sfn.Condition.stringEquals('$.Job.Status.JobRun.State', 'FAILED'))),
            new sfn.Fail(this, 'failed'))
            .otherwise(
              // If conditions are not met, the emr job is still running -> wait and call the "getJobRun" API again
              new sfn.Wait(this, 'wait', { time: sfn.WaitTime.duration(cdk.Duration.seconds(intervalInSeconds)) })
                .next(checkTask)
            )
        )
      )
    new sfn.StateMachine(this, 'emr-serverless-state-machine', {
      definition: startState,
    });
  }
}
