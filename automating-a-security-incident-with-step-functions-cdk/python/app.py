#!/usr/bin/env python3
import aws_cdk as cdk

from stack import (
    AutomateSecurityIncidentStack,
)


app = cdk.App()
AutomateSecurityIncidentStack(
    app,
    construct_id="AutomateSecurityIncidentStack",
    admin_email_address="test@example.com",
    restricted_actions="s3:DeleteObjectVersion,s3:DeleteBucket",
)

app.synth()
