import os
import aws_cdk as cdk
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_iam as iam
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_s3 as s3
from constructs import Construct

LAMBDAS_DIR = os.path.join(os.path.dirname(__file__), "../lambdas")


class LambdaComputeConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        jobs_table: dynamodb.Table,
        input_bucket: s3.Bucket,
        output_bucket: s3.Bucket,
        bedrock_service_role_arn: str,
        model_id: str,
        timeout_duration_hours: int,
        batch_cutoff_seconds: int,
        max_concurrency: int,
        stuck_threshold_minutes: int,
    ) -> None:
        super().__init__(scope, construct_id)

        self.execution_role = iam.Role(
            self, "LambdaExecutionRole",
            role_name="bedrock-batch-sla-lambda-execution",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )

        region = cdk.Stack.of(self).region
        account = cdk.Stack.of(self).account

        # InvokeModel uses inference-profile ARN for cross-region profiles, foundation-model ARN otherwise
        # CreateModelInvocationJob is scoped to * because cross-region profiles route to foundation
        # models in any region, and IAM checks that target region's ARN which cannot be predicted at deploy time
        if model_id.split(".")[0] in ("us", "eu", "ap"):
            invoke_arn = f"arn:aws:bedrock:{region}:{account}:inference-profile/{model_id}"
            base_model_id = ".".join(model_id.split(".")[1:])
        else:
            invoke_arn = f"arn:aws:bedrock:{region}::foundation-model/{model_id}"
            base_model_id = model_id
        batch_job_model_arn = f"arn:aws:bedrock:{region}::foundation-model/{base_model_id}"

        # CreateModelInvocationJob must be scoped to * — AWS prescribes this in the batch inference
        # permissions guide (docs.aws.amazon.com/bedrock/latest/userguide/batch-inference-permissions.html).
        # Cross-region profiles route the job to whichever region has capacity, so the target
        # foundation-model ARN cannot be predicted at deploy time.
        self.execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:CreateModelInvocationJob"],
            resources=["*"],
        ))

        self.execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel"],
            resources=[invoke_arn],
        ))

        self.execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:GetModelInvocationJob",
                "bedrock:ListModelInvocationJobs",
                "bedrock:StopModelInvocationJob",
            ],
            resources=[f"arn:aws:bedrock:{region}:{account}:model-invocation-job/*"],
        ))

        self.execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["iam:PassRole"],
            resources=[bedrock_service_role_arn],
        ))

        jobs_table.grant_read_write_data(self.execution_role)
        input_bucket.grant_read(self.execution_role)
        output_bucket.grant_read_write(self.execution_role)

        self.execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["states:SendTaskSuccess", "states:SendTaskFailure"],
            resources=[f"arn:aws:states:{region}:{account}:stateMachine:*"],
        ))

        self.execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["states:StartExecution"],
            resources=[f"arn:aws:states:{region}:{account}:stateMachine:*"],
        ))

        code = lambda_.Code.from_asset(LAMBDAS_DIR)
        runtime = lambda_.Runtime.PYTHON_3_13

        self.registrar_fn = lambda_.Function(
            self, "RegistrarFunction",
            function_name="bedrock-batch-sla-registrar",
            runtime=runtime,
            handler="registrar/index.handler",
            code=code,
            role=self.execution_role,
            environment={
                "JOBS_TABLE_NAME": jobs_table.table_name,
                "OUTPUT_BUCKET_NAME": output_bucket.bucket_name,
                "MODEL_ID": model_id,
                "STATE_MACHINE_ARN": "",  # Updated after state machine is created
            },
            timeout=cdk.Duration.seconds(60),
            memory_size=256,
            tracing=lambda_.Tracing.ACTIVE,
        )

        self.store_token_fn = lambda_.Function(
            self, "StoreTokenFunction",
            function_name="bedrock-batch-sla-store-token",
            runtime=runtime,
            handler="store-token/index.handler",
            code=code,
            role=self.execution_role,
            environment={
                "JOBS_TABLE_NAME": jobs_table.table_name,
                "MODEL_ID": model_id,
            },
            timeout=cdk.Duration.seconds(30),
            memory_size=128,
            tracing=lambda_.Tracing.ACTIVE,
        )

        self.resume_fn = lambda_.Function(
            self, "ResumeFunction",
            function_name="bedrock-batch-sla-resume",
            runtime=runtime,
            handler="resume/index.handler",
            code=code,
            role=self.execution_role,
            environment={
                "JOBS_TABLE_NAME": jobs_table.table_name,
            },
            timeout=cdk.Duration.seconds(60),
            memory_size=128,
            tracing=lambda_.Tracing.ACTIVE,
        )

        self.trigger_fn = lambda_.Function(
            self, "TriggerFunction",
            function_name="bedrock-batch-sla-trigger",
            runtime=runtime,
            handler="trigger/index.handler",
            code=code,
            role=self.execution_role,
            environment={
                "JOBS_TABLE_NAME": jobs_table.table_name,
                "MODEL_ID": model_id,
            },
            timeout=cdk.Duration.seconds(60),
            memory_size=256,
            tracing=lambda_.Tracing.ACTIVE,
        )

        self.reconcile_fn = lambda_.Function(
            self, "ReconcileFunction",
            function_name="bedrock-batch-sla-reconcile",
            runtime=runtime,
            handler="reconcile/index.handler",
            code=code,
            role=self.execution_role,
            environment={
                "OUTPUT_BUCKET_NAME": output_bucket.bucket_name,
            },
            timeout=cdk.Duration.seconds(300),
            memory_size=512,
            tracing=lambda_.Tracing.ACTIVE,
        )

        self.merge_fn = lambda_.Function(
            self, "MergeFunction",
            function_name="bedrock-batch-sla-merge",
            runtime=runtime,
            handler="merge/index.handler",
            code=code,
            role=self.execution_role,
            environment={
                "OUTPUT_BUCKET_NAME": output_bucket.bucket_name,
            },
            timeout=cdk.Duration.seconds(300),
            memory_size=512,
            tracing=lambda_.Tracing.ACTIVE,
        )

    def update_registrar_state_machine_arn(self, state_machine_arn: str) -> None:
        self.registrar_fn.add_environment("STATE_MACHINE_ARN", state_machine_arn)
