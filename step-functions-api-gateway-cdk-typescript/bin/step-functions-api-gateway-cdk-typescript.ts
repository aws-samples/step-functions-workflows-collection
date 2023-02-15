
import * as cdk from 'aws-cdk-lib';

import { StepFunctionsApiGatewayCdkTypescriptStack } from '../lib/step-functions-api-gateway-cdk-typescript-stack';
import { APIStack } from '../lib/apistack';

const app = new cdk.App();
const apiStack = new APIStack(app, 'APIStack');

const stepfnStack = new StepFunctionsApiGatewayCdkTypescriptStack(app, 'StepFunctionsApiGatewayCdkTypescriptStack',{
    restApi : apiStack.restApi
});

stepfnStack.addDependency(apiStack);

app.synth();