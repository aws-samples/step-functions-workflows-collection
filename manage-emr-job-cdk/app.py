#!/usr/bin/env python3

import aws_cdk as cdk

from manage_emr_job.manage_emr_job_stack import ManageEmrJobStack


app = cdk.App()
ManageEmrJobStack(app, "manage-emr-job")

app.synth()
