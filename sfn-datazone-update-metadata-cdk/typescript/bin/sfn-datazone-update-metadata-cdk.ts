#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SfnDataZoneUpdateMetadataCdkStack } from '../lib/sfn-datazone-update-metadata-cdk-stack';

const app = new cdk.App();

new SfnDataZoneUpdateMetadataCdkStack(app, 'SfnDataZoneUpdateMetadataCdkStack', {
  env: { region: 'eu-central-1' }
  /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
});