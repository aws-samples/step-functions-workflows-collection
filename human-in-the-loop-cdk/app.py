#!/usr/bin/env python3
import aws_cdk as cdk

from human_in_the_loop_cdk.human_in_the_loop_cdk_stack import HumanInTheLoopCdkStack


app = cdk.App()
HumanInTheLoopCdkStack(app, "HumanInTheLoopCdkStack")

app.synth()
