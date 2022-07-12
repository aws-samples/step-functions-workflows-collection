#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { IdempotentStepfunctionsWorkflowStack } from '../lib/idempotent-stepfunctions-workflow-stack';

const app = new cdk.App();
new IdempotentStepfunctionsWorkflowStack(app, 'IdempotentStepfunctionsWorkflowStack', {});