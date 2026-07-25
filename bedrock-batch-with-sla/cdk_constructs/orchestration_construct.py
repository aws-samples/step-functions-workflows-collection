import json
import os
import aws_cdk as cdk
import aws_cdk.aws_stepfunctions as sfn
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_s3 as s3
from constructs import Construct

ASL_PATH = os.path.join(os.path.dirname(__file__), "../statemachine/statemachine.asl.json")


class OrchestrationConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        region: str,
        store_token_fn: lambda_.Function,
        reconcile_fn: lambda_.Function,
        merge_fn: lambda_.Function,
        bedrock_service_role_arn: str,
        jobs_table: dynamodb.Table,
        output_bucket: s3.Bucket,
        model_id: str,
        batch_cutoff_seconds: int,
        timeout_duration_hours: int,
        max_concurrency: int,
    ) -> None:
        super().__init__(scope, construct_id)

        self.execution_role = iam.Role(
            self, "StateMachineRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )

        account_id = cdk.Stack.of(self).account

        self.execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["lambda:InvokeFunction"],
            resources=[store_token_fn.function_arn, reconcile_fn.function_arn, merge_fn.function_arn],
        ))

        # InvokeModel uses inference-profile ARN for cross-region profiles, foundation-model ARN otherwise
        # CreateModelInvocationJob is scoped to * because cross-region profiles route to foundation
        # models in any region, and IAM checks that target region's ARN which cannot be predicted at deploy time
        if model_id.split(".")[0] in ("us", "eu", "ap"):
            invoke_arn = f"arn:aws:bedrock:{region}:{account_id}:inference-profile/{model_id}"
            base_model_id = ".".join(model_id.split(".")[1:])  # strip region prefix e.g. us.
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
            actions=["bedrock:StopModelInvocationJob"],
            resources=[f"arn:aws:bedrock:{region}:{account_id}:model-invocation-job/*"],
        ))

        self.execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["iam:PassRole"],
            resources=[bedrock_service_role_arn],
        ))

        self.execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["dynamodb:UpdateItem", "dynamodb:GetItem"],
            resources=[jobs_table.table_arn],
        ))

        self.execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject", "s3:PutObject"],
            resources=[f"{output_bucket.bucket_arn}/*"],
        ))

        self.execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["states:StartExecution"],
            resources=[f"arn:aws:states:{region}:{account_id}:stateMachine:*"],
        ))

        try:
            with open(ASL_PATH) as f:
                asl = f.read()
            asl = (
                asl
                .replace("${StoreTokenFunctionArn}", store_token_fn.function_arn)
                .replace("${ReconcileFunctionArn}", reconcile_fn.function_arn)
                .replace("${MergeFunctionArn}", merge_fn.function_arn)
                .replace("${BedrockServiceRoleArn}", bedrock_service_role_arn)
                .replace("${ModelId}", model_id)
                .replace("${BatchCutoffSeconds}", str(batch_cutoff_seconds))
                .replace("${TimeoutDurationHours}", str(timeout_duration_hours))
                .replace("${MaxConcurrency}", str(max_concurrency))
                .replace("${OutputBucket}", output_bucket.bucket_name)
                .replace("${JobsTableName}", jobs_table.table_name)
                .replace("${Region}", region)
            )
        except FileNotFoundError:
            print("WARNING: ASL definition file not found, creating placeholder state machine")
            asl = json.dumps({
                "Comment": "Placeholder - ASL definition not yet created",
                "StartAt": "Placeholder",
                "States": {
                    "Placeholder": {"Type": "Pass", "Result": "ASL definition pending", "End": True}
                },
            })

        # L1 CfnStateMachine used instead of L2 StateMachine because definition_substitutions
        # only accepts str values (Fn::Sub), which would quote numeric fields like
        # TimeoutSeconds and MaxConcurrency, failing Step Functions schema validation.
        self.state_machine = sfn.CfnStateMachine(
            self, "StateMachine",
            state_machine_name="bedrock-batch-sla-fallback",
            role_arn=self.execution_role.role_arn,
            definition_string=asl,
            state_machine_type="STANDARD",
            tags=[sfn.CfnStateMachine.TagsEntryProperty(key="project", value="bedrock-batch-sla")],
        )

        self.state_machine_arn = self.state_machine.attr_arn
