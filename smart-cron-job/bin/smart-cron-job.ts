#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SmartCronJobStack } from '../lib/smart-cron-job-stack';

const app = new cdk.App();
new SmartCronJobStack(app, 'SmartCronJobStack');