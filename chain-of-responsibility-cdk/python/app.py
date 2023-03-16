from aws_cdk import (
    App,
    CfnOutput,
    Stack,
    aws_lambda as _lambda,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)

from constructs import Construct


class chainOfResponseStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Define the deispens functions 50, 20, 10 and 1
        dispense_50_function = _lambda.Function(self, "dispense-50-function",
            code=_lambda.Code.from_asset("./functions/handler1"),
            handler="app.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_9                                   
        )

        dispense_20_function = _lambda.Function(self, "dispense-20-function",
            code=_lambda.Code.from_asset("./functions/handler2"),
            handler="app.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_9                                   
        )

        dispense_10_function = _lambda.Function(self, "dispense-10-function",
            code=_lambda.Code.from_asset("./functions/handler3"),
            handler="app.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_9                                   
        )

        dispense_1_function = _lambda.Function(self, "dispense-1-function",
            code=_lambda.Code.from_asset("./functions/handler4"),
            handler="app.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_9                                   
        )

        # define the stepfunction statemachine definition 
        job_50 = tasks.LambdaInvoke(self, "Dispense50",
            lambda_function=dispense_50_function,
            output_path="$.Payload")
        job_20 = tasks.LambdaInvoke(self, "Dispense20",
            lambda_function=dispense_20_function,
            output_path="$.Payload")
        job_10 = tasks.LambdaInvoke(self, "Dispense10",
            output_path="$.Payload",
            lambda_function=dispense_10_function,)
        job_1 = tasks.LambdaInvoke(self, "Dispense1",
            output_path="$.Payload",
            lambda_function=dispense_1_function,)
        
        step_function_def = sfn.Chain.start(job_50).next(job_20).next(job_10).next(job_1)

        # state machine
        state_machine = sfn.StateMachine(self, "ChainedStateMachine",
            definition=step_function_def,
        )

        # output of the stack
        CfnOutput(self, "StateMachineArn", value=state_machine.state_machine_arn)
        CfnOutput(self, "StateMachineRoleArn", value=state_machine.role.role_arn)


app = App()
chainOfResponseStack(
    app,
    "ChainOfResponse",
)
app.synth()