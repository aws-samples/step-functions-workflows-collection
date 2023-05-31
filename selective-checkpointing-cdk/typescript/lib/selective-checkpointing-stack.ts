import * as cdk from 'aws-cdk-lib';
import {Construct} from 'constructs';
import {ChildStateMachine} from "./child-state-machine";
import {ParentStateMachine} from "./parent-state-machine";

export class SelectiveCheckpointingStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // Template Options
        this.templateOptions.description = 'Sample CDK Stack for selective checkpointing';

        const childStateMachine = new ChildStateMachine(this, 'ChildStateMachine');

        const parentStateMachine = new ParentStateMachine(this, 'ParentStateMachine', childStateMachine.Arn);
    }
}
