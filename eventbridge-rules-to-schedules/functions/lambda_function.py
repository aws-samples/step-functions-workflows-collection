import boto3
import json

from scheduler_params import get_params  # Custom python script

# Can process upto 260K rules + targets combination
# 1000 rules - 95 Execution Events

# CONSTANTS
MAX_RULES = 150  # Maximum number of rules to process in one iteration (Changing this May hit SF Payload limit 256 KB)
MAX_S3_RULES = 260000  # Maximum number of rules to process in one iteration from S3
MAX_INLINE_RULES = 50  # Maximum number of rules to process in one iteration from Step Functions input payload
RULE_STATES = {'ENABLED', 'DISABLED', 'PRESERVED'}
SCHEDULE_STATES = {'ENABLED', 'DISABLED'}

# Upperbound - Hard-limit (DO NOT CHANGE) - AWS API
MAX_LIMIT_LIST_RULES = 100  # Max number of rules returned in a single call to list_rules

# BOTO3 CLIENTS
events_client = boto3.client('events')  # boto3 client for events
s3_client = boto3.client('s3')  # boto3 client for S3


def filter_rules_and_target(rules, custom=False):
    rules_with_targets = []
    for rule in rules:
        # Only rules with ScheduleExpression can be transferred to Scheduler.
        if 'ScheduleExpression' in rule:
            targets = events_client.list_targets_by_rule(
                Rule=rule['Name'],
                Limit=6  # Maximum 5 targets per rule
            )
            i = 0
            target_count = len(targets['Targets'])
            for target in targets['Targets']:
                if 'InputPath' in target or 'InputTransformer' in target:
                    pass  # Cannot process these type of targets
                else:
                    additional_keys = {
                        'Index': i,  # Used for Schedule Name for rules that has multiple targets
                        'Target': target,
                        'Description': rule.get('Description', ''),  # Add blank description
                        'TargetCount': target_count,  # Add TargetCount for rules that has multiple targets
                    }
                    # Remove RuleState if custom=False.
                    if not custom:
                        rule.pop('RuleState', None)
                    rules_with_targets.append({**rule, **additional_keys})
                    i += 1
    return rules_with_targets


def get_rules_using_names(input_rules, next_token=None):
    # Each rule can have maximum 5 targets
    # https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html
    rules_with_targets = []
    rules = []

    # next_token here is an index (digit)
    # If next_token is present it indicates that the rule array needs to be sliced.
    if next_token:
        end_index = int(next_token) + MAX_RULES
        input_rules_sliced = input_rules[int(next_token): end_index]
        next_token = end_index if end_index < len(input_rules) else None
    else:
        input_rules_sliced = input_rules[:MAX_RULES]
        next_token = MAX_RULES if len(input_rules_sliced) < len(input_rules) else None

    # For each rule in input_rules 'Describe' the rule using RuleName
    for rule in input_rules_sliced:
        rule_description = events_client.describe_rule(Name=rule['RuleName'])
        rules.append({**rule_description, **rule})

    # filter transferable rules
    # custom=True is used to mention that the rule description is obtained using RuleName in describe_rule.
    rules_with_targets += filter_rules_and_target(rules, custom=True)

    return rules_with_targets, str(next_token) if next_token is not None else next_token


def get_rules(next_token=None):
    # Each rule can have maximum 5 targets
    # https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html
    rules_with_targets = []

    # Get list of rules in the default bus and filter transferable rules.
    if next_token:
        rules = events_client.list_rules(Limit=MAX_LIMIT_LIST_RULES, NextToken=next_token)  # list rules in default bus
    else:
        rules = events_client.list_rules(Limit=MAX_LIMIT_LIST_RULES)  # list rules in default bus

    rules_with_targets += filter_rules_and_target(rules['Rules'])  # filter transferable rules

    # Keep on fetching rules with target till the number equals to MAX_RULES to process
    while 'NextToken' in rules and len(rules_with_targets) <= MAX_RULES:
        # list rules in default bus
        rules = events_client.list_rules(Limit=MAX_LIMIT_LIST_RULES, NextToken=rules['NextToken'])
        # filter transferable rules
        rules_with_targets += filter_rules_and_target(rules['Rules'])

    next_token = rules.get('NextToken')  # Will be "None" if NexToken is not present.
    return rules_with_targets, next_token


def validate_states(event, set_default=True):
    # How should the state of the EventBridge Rule be?
    # ENABLED - Make the state of the rule ENABLED
    # DISABLED - Make the state of the rule DISABLED
    # PRESERVED - Do not modify the state of the rule
    # Default - DISABLED
    if 'RuleState' in event:
        if type(event['RuleState']) != str:
            raise Exception('Invalid RuleState type. It must be a string.')
        if event['RuleState'] not in RULE_STATES:
            raise Exception(f'Invalid RuleState. It must be {RULE_STATES}.')
    else:
        if set_default:  # Only set default if set_default is True
            event['RuleState'] = 'DISABLED'  # set default
    # How should the state of the EventBridge Scheduler be?
    # ENABLED - Enable the new Scheduler
    # DISABLED - Disable the new Scheduler
    # Default - ENABLED
    if 'ScheduleState' in event:
        if type(event['ScheduleState']) != str:
            raise Exception('Invalid ScheduleState type. It must be a string.')
        if event['ScheduleState'] not in SCHEDULE_STATES:
            raise Exception(f'Invalid ScheduleState. It must be {SCHEDULE_STATES}.')
    else:
        if set_default:  # Only set default if set_default is True
            event['ScheduleState'] = 'ENABLED'  # set default


def validate_rules(event, rules):
    for rule in rules:
        rule_level_keys = {'RuleName', 'ScheduleRoleArn', 'ScheduleName', 'ScheduleGroup', 'RuleState',
                           'ScheduleState'}  # set
        invalid_keys = rule.keys() - rule_level_keys  # set difference
        if invalid_keys:
            raise Exception(f'Invalid key/s {invalid_keys}')
        # RuleName and ScheduleRoleArn are required
        if 'RuleName' not in rule:
            raise Exception('RuleName is required in Rules.')
        if 'ScheduleRoleArn' not in event and 'ScheduleRoleArn' not in rule:
            raise Exception('ScheduleRoleArn is required at root level or in the Rule object of Rules.')
        validate_states(rule, set_default=False)  # Validate RuleState and ScheduleState


# Lambda Handler
def lambda_handler(event, context):
    # ----------------------------------------------------
    # Performing Event payload verification
    # ----------------------------------------------------

    # Verify root level keys
    root_level_keys = {'ScheduleRoleArn', 'RuleState', 'ScheduleState', 'ScheduleGroup', 'Rules',
                       'RulesS3Uri', 'ProcessRules'}  # set
    invalid_keys = set(event.keys()) - root_level_keys  # Set difference
    if invalid_keys:  # if there are keys that are not in the root_level_keys then raise exception
        raise Exception(f'Invalid key/s {invalid_keys}')

    validate_states(event)  # Validating values of RuleState and ScheduleState in the Event payload

    # If both Rules and RulesS3Uri are provided then raise exception
    # Only one of them can be processed
    if 'Rules' in event and 'RulesS3Uri' in event:
        raise Exception(f'Invalid Input. Please provide either "Rules" or "RulesS3Uri" or none of them but not both.')

    # ----------------------------------------------------
    # 3 Types of Rule transfer
    #   A) Rules - List of Rules provided in the Step Functions payload
    #   B) RulesS3Uri - List of Rules provided in S3 key
    #   C) All the rules in the default bus if Rules and RulesS3Uri keys are missing
    # ----------------------------------------------------
    if 'Rules' in event:  # Verify custom rules
        if len(event['Rules']) > MAX_INLINE_RULES:
            raise Exception(f'Maximum {MAX_INLINE_RULES} inline rules are supported. Use RulesS3Uri for larger batch.')
        validate_rules(event, event['Rules'])  # Validating custom rules
        # Get list of 'transferable' rules to convert to schedule
        rules, next_token = get_rules_using_names(event['Rules'])
    elif 'RulesS3Uri' in event:  # Custom rules in S3
        uri = event['RulesS3Uri']
        try:
            bucket, key = uri.split('//')[1].split('/', 1)  # Get bucket and key from S3 URI
        except Exception as e:
            raise Exception(f'Invalid S3 URI. {e}')
        response = s3_client.get_object(Bucket=bucket, Key=key)  # Download the rules file from s3
        s3_rules = json.loads(response['Body'].read())  # Load the rules from the downloaded file
        if len(s3_rules) > MAX_S3_RULES:
            raise Exception(f'Maximum rules in RulesS3Uri should be less than {MAX_S3_RULES}.')
        validate_rules(event, s3_rules)  # Validating custom rules

        # isdigit is used to differentiate between custom integer next token (list indices) vs aws api UUID4 next token
        token = ((event.get('ProcessRules', {}) or {}).get('Lambda', {}) or {}).get('NextToken')
        if token and token.isdigit():
            # Get list of 'transferable' rules to convert to schedule
            rules, next_token = get_rules_using_names(s3_rules, token)
        else:
            # Get list of 'transferable' rules to convert to schedule
            rules, next_token = get_rules_using_names(s3_rules)
    else:
        token = ((event.get('ProcessRules', {}) or {}).get('Lambda', {}) or {}).get('NextToken')
        # All the rules in default bus
        if token:
            # Get list of 'transferable' rules to convert to schedule
            rules, next_token = get_rules(token)  # next token will be UUID4
        else:
            # Get list of 'transferable' rules to convert to schedule
            rules, next_token = get_rules()  # next token will be UUID4

    if rules:
        create_schedule_params_list = []  # List of parameters to be passed to CreateSchedule for each rule

        # Create parameters for create_schedule for each rule
        for rule in rules:
            # Get parameters for CreateSchedule
            params = get_params({
                'Rule': rule,
                'RuleState': event['RuleState'],
                'ScheduleState': event['ScheduleState'],
                'ScheduleRoleArn': rule.get('ScheduleRoleArn') or event['ScheduleRoleArn'],
                'ScheduleGroup': event.get('ScheduleGroup', ''),  # ScheduleGroup can be blank
            })
            # If params contain target - it indicates that the rule is transferable to schedule
            if params['Target']:  # Target can be blank
                create_schedule_params_list.append(params)
        # If there are params to create schedule then return them
        if create_schedule_params_list:
            response = {'ParamsList': create_schedule_params_list}
        else:
            raise Exception('No rules to process that match the criteria.')
    else:
        # No rules are present that match the criteria
        raise Exception('No rules to process that match the criteria.')

    # Add the new NextToken if present
    if next_token:
        response['NextToken'] = next_token
    return response
