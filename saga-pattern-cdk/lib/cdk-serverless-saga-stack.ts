import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { StateMachine } from './stateMachine';

export class CdkServerlessSagaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const stateMachine = new StateMachine(this, 'StateMachine');
  }
}
