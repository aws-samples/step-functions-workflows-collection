#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { ImageProcessingAppStack } from "../lib/image-processing-app-stack";

const app = new cdk.App();
new ImageProcessingAppStack(app, "ImageProcessingAppStack");
