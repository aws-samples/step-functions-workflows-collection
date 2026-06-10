#!/usr/bin/env python3
import aws_cdk as cdk

from cdk.cdk_stack import HumanInTheLoopCdkStack


app = cdk.App()
HumanInTheLoopCdkStack(app, "HumanInTheLoopCdkStack")

app.synth()
