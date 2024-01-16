#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { TranscodeWorkflowStack } from '../lib/transcode-workflow';
import { ErrorHanlderStack } from '../lib/error-handler';
import { SharedResourcesStack } from '../lib/shared-resource';
import { UiS3UploadStack } from '../lib/ui-upload-s3';
import { TranscriptBedrockWorkflowStack } from '../lib/transcript-bedrock-workflow';

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT, 
  region: process.env.CDK_DEFAULT_REGION, 
};

const sharedResourcesStack = new SharedResourcesStack(app, 'SharedResourcesStack', {
  // subEmail: 'you@email.address',
  subEmail: 'fanhongy@amazon.com',
  env: env
});

const errorHanlderStack = new ErrorHanlderStack(app, 'ErrorHandlerStack',{
  env: env
});

const transcodeWorkflowStack = new TranscodeWorkflowStack(app, 'MediaTranscodeStack', {
  env: env
});

const uiS3UploadStack = new UiS3UploadStack(app, 'UiUploadS3Stack', {
  env: env
});

const transcriptBedrockWorkflowStack = new TranscriptBedrockWorkflowStack(app, "TranscriptBedrockWorkflowStack", {
  env: env
});


// Add stack dependencies 
transcodeWorkflowStack.addDependency(sharedResourcesStack);
errorHanlderStack.addDependency(sharedResourcesStack);
uiS3UploadStack.addDependency(sharedResourcesStack);
transcriptBedrockWorkflowStack.addDependency(sharedResourcesStack);