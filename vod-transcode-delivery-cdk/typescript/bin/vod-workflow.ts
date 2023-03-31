#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { TranscodeWorkflowStack } from "../lib/transcode-workflow";
import { DeliverChannelStack } from "../lib/deliver-channel";
import { ErrorHanlderStack } from "../lib/error-handler";
import { SharedResourcesStack } from "../lib/shared-resource";

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT, 
  region: process.env.CDK_DEFAULT_REGION, 
};

const sharedResourcesStack = new SharedResourcesStack(app, "SharedResourcesStack", {
  subEmail: "you@email.address",
  env: env
});

const errorHanlderStack = new ErrorHanlderStack(app, "ErrorHandlerStack",{
  env: env
});

const transcodeWorkflowStack = new TranscodeWorkflowStack(app, "MediaTranscodeStack", {
  env: env
});

const deliverChannelStack = new DeliverChannelStack(app, "DeliverChannelStack", {
  env: env,
  assetBucket: transcodeWorkflowStack.assestBucket,
  enableCdnAuth: true,
});


// Add stack dependencies 
deliverChannelStack.addDependency(transcodeWorkflowStack)
deliverChannelStack.addDependency(sharedResourcesStack)
transcodeWorkflowStack.addDependency(sharedResourcesStack)
errorHanlderStack.addDependency(sharedResourcesStack)
