import aws_cdk as cdk
import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3
from constructs import Construct


class BedrockServiceConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str,
                 input_bucket: s3.IBucket, output_bucket: s3.IBucket,
                 model_id: str) -> None:
        super().__init__(scope, construct_id)

        region = cdk.Stack.of(self).region

        self.service_role = iam.Role(
            self, "BedrockServiceRole",
            role_name="bedrock-batch-sla-service-role",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Service role for Bedrock batch inference jobs",
        )

        self.service_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject", "s3:ListBucket"],
            resources=[input_bucket.bucket_arn, f"{input_bucket.bucket_arn}/*"],
        ))

        self.service_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:PutObject", "s3:ListBucket"],
            resources=[output_bucket.bucket_arn, f"{output_bucket.bucket_arn}/*"],
        ))

        # Cross-region inference profiles use inference-profile ARN; base models use foundation-model ARN
        if model_id.split(".")[0] in ("us", "eu", "ap"):
            profile_arn = f"arn:aws:bedrock:{region}:{cdk.Stack.of(self).account}:inference-profile/{model_id}"
            base_model_id = ".".join(model_id.split(".")[1:])
            self.service_role.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[profile_arn],
            ))
            # Cross-region profiles route to foundation models in destination regions at runtime.
            # Wildcard region with InferenceProfileArn condition avoids hardcoding destination regions.
            # See: docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html
            self.service_role.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[f"arn:aws:bedrock:*::foundation-model/{base_model_id}"],
                conditions={"StringEquals": {"bedrock:InferenceProfileArn": profile_arn}},
            ))
        else:
            self.service_role.add_to_policy(iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[f"arn:aws:bedrock:{region}::foundation-model/{model_id}"],
            ))

        self.service_role_arn = self.service_role.role_arn
