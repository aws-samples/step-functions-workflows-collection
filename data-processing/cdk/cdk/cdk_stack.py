import aws_cdk as cdk
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_dynamodb as dynamo_db
import aws_cdk.aws_stepfunctions as step_functions
import aws_cdk.aws_iam as iam
import os
            
class CdkStack(cdk.Stack):

    def __init__(self, scope: cdk.App, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get Account and Region
        account = os.environ["CDK_DEFAULT_ACCOUNT"]
        region = os.environ["CDK_DEFAULT_REGION"]

        # Create S3 Bucket
        bucket_name_value = "data-workflow-pattern-" + account + "-" + region
        s3.Bucket(self, bucket_name_value, bucket_name=bucket_name_value, removal_policy=cdk.RemovalPolicy.DESTROY, auto_delete_objects=True)

        # Create DynamoDB Table
        dynamo_table_name= "images-data-workflow-pattern-sl"
        dynamo_db.Table(
            self, dynamo_table_name, table_name=dynamo_table_name, removal_policy=cdk.RemovalPolicy.DESTROY,
            partition_key=dynamo_db.Attribute(
                name="id",
                type=dynamo_db.AttributeType.STRING
            )
        )
        
        # IAM role for the state machine
        stepfunction_service_principal = "states." + region + ".amazonaws.com"
        role = iam.Role(self, "stepfunctions-data-patterns-role",
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('AmazonRekognitionReadOnlyAccess'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess')],
            assumed_by=iam.ServicePrincipal(stepfunction_service_principal),
        )
        
        # Create State Machine
        statemachine_definition = self.read_statemachine_definition()
        print(statemachine_definition)
        step_functions.CfnStateMachine(
            self, "ProcessImageDataPatternStateMachine",
            definition_string=statemachine_definition,
            role_arn=role.role_arn
        )
        
    # Reads state machine ASL definition from local file
    def read_statemachine_definition(self):
        input_file_name = "statemachine/statemachine.asl.json"
        read_file = open(input_file_name, "rt")
        file_contents = read_file.read()
        read_file.close()
        return file_contents