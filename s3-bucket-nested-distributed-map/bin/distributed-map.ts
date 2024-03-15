#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { DistributedMapStack } from '../lib/distributed-map-stack';

const app = new cdk.App();
new DistributedMapStack(app, 'distributed-map-stack');