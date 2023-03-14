import {
    App, 
    CfnOutput,
    aws_lambda as lambda,
    Stack,
    StackProps,
    aws_stepfunctions as sfn, 
    aws_stepfunctions_tasks as tasks 
} from "aws-cdk-lib"

import { Construct } from "constructs"

export class chainOfResponseStack extends Stack {
    constructor (
        scope: Construct,
        id: string,
        props: StackProps)
        {
        super(scope, id, props);

        // define the dispense functions: 50, 20, 10 and 1
        const dispense50Function = new lambda.Function(this, 'dispense-50-fuction', {
            code: lambda.Code.fromAsset('./functions/handler1'),
            handler: "app.lambda_handler",
            runtime: lambda.Runtime.PYTHON_3_9,
          }
        );
        
        const dispense20Function = new lambda.Function(this, 'dispense-20-fuction', {
            code: lambda.Code.fromAsset('./functions/handler2'),
            handler: "app.lambda_handler",
            runtime: lambda.Runtime.PYTHON_3_9,
          }
        );

        const dispense10Function = new lambda.Function(this, 'dispense-10-fuction', {
            code: lambda.Code.fromAsset('./functions/handler3'),
            handler: "app.lambda_handler",
            runtime: lambda.Runtime.PYTHON_3_9,
          }
        );

        const dispense1Function = new lambda.Function(this, 'dispense-1-fuction', {
            code: lambda.Code.fromAsset('./functions/handler4'),
            handler: "app.lambda_handler",
            runtime: lambda.Runtime.PYTHON_3_9,
          }
        );

        // define the statemachine definition
        const job_50 = new tasks.LambdaInvoke(this, "dispense 50",{
            lambdaFunction: dispense50Function,
            outputPath: "$.Payload"
        });
        const job_20 = new tasks.LambdaInvoke(this, "dispense 20",{
            lambdaFunction: dispense20Function,
            outputPath: "$.Payload"
        });
        const job_10 = new tasks.LambdaInvoke(this, "dispense 10",{
            lambdaFunction: dispense10Function,
            outputPath: "$.Payload"
        });
        const job_1 = new tasks.LambdaInvoke(this, "dispense 1",{
            lambdaFunction: dispense1Function,
            outputPath: "$.Payload"
        });
        
        // build the state machine 
        const stepFunctionDef = sfn.Chain.start(job_50).next(job_20).next(job_10).next(job_1)
       
        const stateMachine = new sfn.StateMachine(this, "chainedStatemachin",{
            definition: stepFunctionDef
        }
        );

        // the output of stack
        new CfnOutput(this, "StateMachinArn", {
            value: stateMachine.stateMachineArn
        }) 
        new CfnOutput(this, "StatemachinRoleArn", {
            value: stateMachine.role.roleArn
        })

    }
}

const app = new App()
new chainOfResponseStack(app, "chainOfResponseStack",{})
app.synth()