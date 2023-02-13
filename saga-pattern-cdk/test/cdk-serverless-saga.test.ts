import { Template, Match } from 'aws-cdk-lib/assertions';
import * as cdk from 'aws-cdk-lib';
import TheSagaStepfunction = require('../lib/cdk-serverless-saga-stack');

let template: Template;

beforeAll(() => {
  const app = new cdk.App();
  const stack = new TheSagaStepfunction.CdkServerlessSagaStack(app, 'MyTestStack');
  template = Template.fromStack(stack);
});

test('API Gateway Proxy Created', () => {
  template.hasResourceProperties("AWS::ApiGateway::Resource", {
    "PathPart": "{proxy+}"
  });
});

test('9 Lambda Functions Created', () => {
  template.resourceCountIs("AWS::Lambda::Function", 9);
});

test('Saga Lambda Permissions To Execute StepFunction', () => {
  template.hasResourceProperties("AWS::IAM::Policy", {
    "PolicyDocument": {
      "Statement": [{
        "Action": "states:StartExecution",
        "Effect": "Allow"
      }]
    }
  });
});

test('3 DynamoDB Tables Created', () => {
  template.resourceCountIs("AWS::DynamoDB::Table", 3);
});

