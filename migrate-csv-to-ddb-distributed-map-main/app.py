#!/usr/bin/env python3
import os

import aws_cdk as cdk

from migrate_csv_to_ddb_distributed_map.migrate_csv_to_ddb_distributed_map_stack import MigrateCSVToDdbDistributedMapStack


app = cdk.App()
MigrateCSVToDdbDistributedMapStack(app, "MigrateCSVToDDBDistributedMapStack"
                                   )

app.synth()
