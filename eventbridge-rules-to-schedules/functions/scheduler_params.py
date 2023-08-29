import json
import re

import boto3


def process_ecs_params(ecs_params):
    # Handling PascalCase for ECS Params for Step Functions.
    # Since Step Function needs Pascal Params for CreateSchedule task.

    # Changing awsvpcConfiguration to AwsvpcConfiguration (CreateSchedule needs PascalCase)
    if 'NetworkConfiguration' in ecs_params:
        if 'awsvpcConfiguration' in ecs_params['NetworkConfiguration']:
            ecs_params['NetworkConfiguration']['AwsvpcConfiguration'] = ecs_params['NetworkConfiguration'].pop(
                'awsvpcConfiguration')

    # Converting all the child keys to PascalCase
    for key in ['CapacityProviderStrategy', 'PlacementConstraints', 'PlacementStrategy']:
        if key in ecs_params:
            new_data = []
            for data in ecs_params[key]:
                for k, v in data.items():
                    new_data.append({k.capitalize(): v})
            ecs_params[key] = new_data
    return ecs_params


def get_target(event):
    schedule_target = {}
    target = event['Rule']['Target']
    arn = target['Arn']

    # ----------------------------------------------------
    # Targets
    # ----------------------------------------------------

    # Lambda Function, Firehose, SNS, Step Functions, CodeBuild, CodePipeline, SQS,
    # Inspector Assessment Template (arn:aws:inspector:eu-west-1:XXXXXXXXXXXX:target/0-XXXXXXXX/template/0-XXXXXXXX)
    if arn.startswith(('arn:aws:lambda:',
                       'arn:aws:firehose:',
                       'arn:aws:sns:',
                       'arn:aws:states:',
                       'arn:aws:codebuild:',
                       'arn:aws:codepipeline:',
                       'arn:aws:inspector:',
                       'arn:aws:sqs:')):
        schedule_target['Arn'] = arn  # Required
        schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required

        if 'Input' in target:
            schedule_target['Input'] = target['Input']

        # Handle special case for SQS FIFO
        if arn.endswith('.fifo') and 'SqsParameters' in target:
            schedule_target['SqsParameters'] = target['SqsParameters']

    # EC2, EBS, Events
    if arn.startswith('arn:aws:events:'):
        if arn.endswith(':target/stop-instance'):  # EC2 StopInstances
            schedule_target['Arn'] = 'arn:aws:scheduler:::aws-sdk:ec2:stopInstances'  # Required
            schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
            schedule_target['Input'] = json.dumps({'InstanceIds': [json.loads(target['Input'])]})
        if arn.endswith('target/reboot-instance'):  # EC2 RebootInstances
            schedule_target['Arn'] = 'arn:aws:scheduler:::aws-sdk:ec2:rebootInstances'  # Required
            schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
            schedule_target['Input'] = json.dumps({'InstanceIds': [json.loads(target['Input'])]})
        if arn.endswith('target/terminate-instance'):  # EC2 TerminateInstances
            schedule_target['Arn'] = 'arn:aws:scheduler:::aws-sdk:ec2:terminateInstances'  # Required
            schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
            schedule_target['Input'] = json.dumps({'InstanceIds': [json.loads(target['Input'])]})
        if arn.endswith('target/create-snapshot'):  # EBS CreateSnapShot
            schedule_target['Arn'] = 'arn:aws:scheduler:::aws-sdk:ec2:createSnapshot'  # Required
            schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
            schedule_target['Input'] = json.dumps({'VolumeId': json.loads(target['Input'])})
        if ':event-bus/' in arn:  # Event Bus
            # Handles Event bus in the same region and same account
            # Handles Event bus in the same region and different account
            # Does not handle event bus in different region
            elements = arn.split(':')
            event_bus_region = elements[3]
            # Check if region is current region
            if event_bus_region == boto3.session.Session().region_name:
                schedule_target['Arn'] = arn  # Required
                schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
                schedule_target['EventBridgeParameters'] = {  # Required
                    'DetailType': 'eventbridge-scheduler',  # Custom Value (Can be changed)
                    'Source': 'eventbridge-scheduler'  # Custom Value (Can be changed)
                }
            # No Input is present in EventBridge Rule. Hence, blank input in Scheduler.

    # EC2 Image Builder
    if arn.startswith('arn:aws:imagebuilder'):
        schedule_target['Arn'] = 'arn:aws:scheduler:::aws-sdk:imagebuilder:startImagePipelineExecution'  # Required
        schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
        schedule_target['Input'] = json.dumps({'ImagePipelineArn': arn, 'ClientToken': '<aws.scheduler.execution-id>'})

    # ECS Run Task
    if arn.startswith('arn:aws:ecs'):
        schedule_target['Arn'] = arn  # Required
        schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
        schedule_target['EcsParameters'] = process_ecs_params(target['EcsParameters'])
        # No "Input" in ECS Run Task

    # Kinesis
    if arn.startswith('arn:aws:kinesis:'):
        schedule_target['Arn'] = arn  # Required
        schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
        if 'Input' in target:
            schedule_target['Input'] = target['Input']
        schedule_target['KinesisParameters'] = {
            'PartitionKey': '<aws.scheduler.execution-id>'
        }

    # SageMaker Pipeline
    if arn.startswith('arn:aws:sagemaker'):
        schedule_target['Arn'] = arn  # Required
        schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
        if 'Input' in target:
            schedule_target['Input'] = target['Input']
        if 'SageMakerPipelineParameters' in target:
            schedule_target['SageMakerPipelineParameters'] = target['SageMakerPipelineParameters']

    # Systems Manager
    if arn.startswith('arn:aws:ssm'):
        if ':automation-definition/' in arn:  # Systems Manager Automation
            schedule_target['Arn'] = 'arn:aws:scheduler:::aws-sdk:ssm:startAutomationExecution'  # Required
            schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
            document_name, document_version = re.search('automation-definition/(.*)$', arn).group(1).split(':')
            start_automation_params = {
                'DocumentName': document_name,
                'DocumentVersion': document_version,
                'Parameters': json.loads(target['Input'])
            }
            schedule_target['Input'] = json.dumps(start_automation_params)
        if ':document/' in arn:  # Systems Manager Run Command
            schedule_target['Arn'] = 'arn:aws:scheduler:::aws-sdk:ssm:sendCommand'  # Required
            schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
            # Not considering version as no way to find the version in the arn
            send_command_params = {
                'DocumentName': re.search('document/(.*)$', arn).group(1)  # Required
            }
            if 'RunCommandParameters' in target and 'RunCommandTargets' in target['RunCommandParameters']:
                send_command_params['Targets'] = target['RunCommandParameters']['RunCommandTargets']

            if 'Input' in target:
                send_command_params['Parameters'] = json.loads(target['Input'])
            schedule_target['Input'] = json.dumps(send_command_params)

    # Redshift Cluster and Redshift Serverless
    if arn.startswith('arn:aws:redshift'):
        elements = arn.split(':')
        redshift_region = elements[3]
        if redshift_region == boto3.session.Session().region_name:
            # Parameters for execute_statement or batch_execute_statement
            redshift_params = {
                'Database': target['RedshiftDataParameters']['Database']  # Required
            }
            if 'Sql' in target['RedshiftDataParameters']:  # If Sql is a string
                schedule_target['Arn'] = 'arn:aws:scheduler:::aws-sdk:redshiftdata:executeStatement'  # Required
                redshift_params['Sql'] = target['RedshiftDataParameters']['Sql']  # Required
            else:  # If Sqls is an array use batch_execute_statement
                schedule_target['Arn'] = 'arn:aws:scheduler:::aws-sdk:redshiftdata:batchExecuteStatement'  # Required
                redshift_params['Sqls'] = target['RedshiftDataParameters']['Sqls']  # Required

            schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required

            if 'DbUser' in target['RedshiftDataParameters']:
                redshift_params['DbUser'] = target['RedshiftDataParameters']['DbUser']
            if 'StatementName' in target['RedshiftDataParameters']:
                redshift_params['StatementName'] = target['RedshiftDataParameters']['StatementName']
            if 'WithEvent' in target['RedshiftDataParameters']:
                redshift_params['WithEvent'] = target['RedshiftDataParameters']['WithEvent']
            if 'SecretManagerArn' in target['RedshiftDataParameters']:
                redshift_params['SecretArn'] = target['RedshiftDataParameters']['SecretManagerArn']
            if arn.startswith('arn:aws:redshift-serverless:'):  # For Redshift Serverless
                redshift_params['WorkgroupName'] = arn  # Name or Arn will work
            else:  # For Redshift Cluster Identifier
                redshift_params['ClusterIdentifier'] = arn[-1]  # Optional

            schedule_target['Input'] = json.dumps(redshift_params)

    # Batch
    if arn.startswith('arn:aws:batch'):
        schedule_target['Arn'] = 'arn:aws:scheduler:::aws-sdk:batch:submitJob'  # Required
        schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required

        batch_input = {
            'JobQueue': arn,
            'JobName': target['BatchParameters']['JobName'],
            'JobDefinition': target['BatchParameters']['JobDefinition']
        }

        if 'ArrayProperties' in target['BatchParameters']:
            batch_input['ArrayProperties'] = target['BatchParameters']['ArrayProperties']
        if 'RetryStrategy' in target['BatchParameters']:
            batch_input['RetryStrategy'] = target['BatchParameters']['RetryStrategy']

        schedule_target['Input'] = json.dumps(batch_input)

    # Glue Workflow
    if arn.startswith('arn:aws:glue'):
        schedule_target['Arn'] = 'arn:aws:scheduler:::aws-sdk:glue:startWorkflowRun'  # Required
        schedule_target['RoleArn'] = event['ScheduleRoleArn']  # Required
        schedule_target['Input'] = json.dumps({'Name': re.search('workflow/(.*)$', arn).group(1)})

    if schedule_target:
        # Adding General Optional Params
        if 'DeadLetterConfig' in target:
            schedule_target['DeadLetterConfig'] = target['DeadLetterConfig']
        if 'RetryPolicy' in target:
            schedule_target['RetryPolicy'] = target['RetryPolicy']

    return schedule_target


def get_params(event):
    # Adding necessary params for CreateSchedule
    # In EventBridge Rule there can be maximum 5 targets per rule.
    # While in EventBridge Scheduler only 1 target is possible to associate with the Schedule (Rule)
    # Example: MyRule-1 where 1 indicates target.
    # There is no FlexibleTimeWindow in EventBridge Rules. Hence, disabling with Mode: OFF

    # Adding Schedule Name
    if event['Rule']['TargetCount'] > 1:
        prefix_name = event['Rule']['ScheduleName'] if 'ScheduleName' in event['Rule'] else event['Rule']['Name']
        schedule_name = f"{prefix_name}-{event['Rule']['Index']}"
    else:
        schedule_name = event['Rule']['ScheduleName'] if 'ScheduleName' in event['Rule'] else event['Rule']['Name']

    create_schedule_params = {
        'Name': schedule_name,  # Required
        'FlexibleTimeWindow': {'Mode': 'OFF'},  # Required
        'ScheduleExpression': event['Rule']['ScheduleExpression'],  # Required
        'Target': get_target(event),  # Processes the target according the Scheduler
        'RuleName': event['Rule']['Name'],  # Needed to enable and disable rule
        'Description': event['Rule'].get('Description', '') or ''  # Optional
    }

    # Adding RuleState to enable or disable rule
    if 'RuleState' in event['Rule']:
        create_schedule_params['RuleState'] = event['Rule']['RuleState']
    else:  # 'RuleState' is in event
        create_schedule_params['RuleState'] = event['RuleState']

    # Adding Schedule State
    if 'ScheduleState' in event['Rule']:
        create_schedule_params['State'] = event['Rule']['ScheduleState']
    else:  # 'ScheduleState' is in event
        create_schedule_params['State'] = event['ScheduleState']

    # Adding Schedule Group
    if 'ScheduleGroup' in event['Rule']:
        create_schedule_params['ScheduleGroup'] = event['Rule']['ScheduleGroup']
    elif 'ScheduleGroup' in event and event['ScheduleGroup']:
        create_schedule_params['ScheduleGroup'] = event['ScheduleGroup']
    else:
        create_schedule_params['ScheduleGroup'] = 'default'  # Default  schedule group

    return create_schedule_params
