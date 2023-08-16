from constructs import Construct
from aws_cdk import (
    App,
    Stack,
    RemovalPolicy,
    Duration,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_event_source,
    aws_s3 as s3,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_logs as logs_
)

from constructs import Construct

class BackgroundCropperCdkStack(Stack): 
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        #s3Bucket
        in_bucket = s3.Bucket(self, "image-upload-2898",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
        out_bucket = s3.Bucket(self, "image-result-2898",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        #Lambda Role
        #full access to S3, logs, Rekognition and sfn
        lambda_role = iam.Role(self, 'lambdaRole', assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"))
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")
        )
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSStepFunctionsFullAccess")
        )
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonRekognitionFullAccess")
        )

        #lambda to call Rekognition to detect labels
        detect_labels_lambda = _lambda.Function(
            self,
            "detect_labels",
            runtime = _lambda.Runtime.PYTHON_3_9,
            handler = "detect_labels.lambda_handler",
            code =_lambda.Code.from_asset("./lambda/detect_labels"),
            timeout= Duration.minutes(15),
            role = lambda_role
        )

        #lambda to crop image background and store to S3
        crop_image_lambda = _lambda.Function(
            self,
            "crop_image",
            runtime = _lambda.Runtime.PYTHON_3_9,
            handler = "crop_img.lambda_handler",
            code = _lambda.Code.from_asset("./lambda/crop_img/Archive.zip"),
            timeout= Duration.minutes(15),
            role = lambda_role
        )
        crop_image_lambda.add_environment('DESTINATION_BUCKET', out_bucket.bucket_name)

        #create step function definition with previous two lambdas
        detect_labels_task = tasks.LambdaInvoke(self, "Detect Labels",
            lambda_function=detect_labels_lambda,
            output_path="$.Payload"
        )

        crop_img_task = tasks.LambdaInvoke(self, "Crop Image",
            lambda_function=crop_image_lambda,
            output_path="$.Payload"
        )

        sfn_def = sfn.Chain.start(detect_labels_task).next(crop_img_task)

        #enabling logging for step function
        logGroup = logs_.LogGroup(self, 'ImgCropperSFNLog')
        #create step function
        state_machine = sfn.StateMachine(self, "ImgCropperSFN", 
            definition=sfn_def,
            logs={
                'destination':logGroup,
                'level': sfn.LogLevel.ALL
            }
        )

        #lambda to trigger step function when image uploaded to S3
        trigger_sf_lambda = _lambda.Function(
            self,
            "trigger_step_function",
            runtime = _lambda.Runtime.PYTHON_3_9,
            handler = "trigger_sf.lambda_handler",
            code =  _lambda.Code.from_asset("./lambda/trigger_sf"),
            timeout= Duration.minutes(15),
            role = lambda_role
        )
        trigger_sf_lambda.add_environment('STEP_FUNCTION_ARN', state_machine.state_machine_arn)

        #add S3 Event to this Lambda
        trigger_sf_lambda.add_event_source(
            lambda_event_source.S3EventSource(in_bucket,
            events=[s3.EventType.OBJECT_CREATED]
        ))


       
app = App()
BackgroundCropperCdkStack(app, "background-cropper-stack", env={'region': 'us-east-1'})
app.synth()