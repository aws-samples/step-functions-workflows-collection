import boto3
import datetime

sfn = boto3.client('stepfunctions')

def lambda_handler(event, context):
    #get the execution history in reverse order so that we get the most recently executed
    #states within the state machine
    execution_arn = event['Execution']['Id']
    resp = sfn.get_execution_history(
                executionArn=execution_arn,
                maxResults=6,
                reverseOrder=True)
    #print(resp)
    # find the Task that failed, and then go back one event to get the
    # TaskStateExited event which has the name of the task that failed
    failed_task = {}
    for index, event in enumerate(resp['events']):
        if event['type'] == 'TaskFailed':
            print(resp['events'][index - 1])
            failed_task['name'] = resp['events'][index - 1]['stateExitedEventDetails']['name']
            failed_task['error'] = resp['events'][index - 1]['stateExitedEventDetails']['output']
            task_timestamp = resp['events'][index - 1]['timestamp']
            failed_task['timestamp'] = task_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(f'Failed task named: {failed_task['name']}, failed with error: {failed_task['error']}, at {failed_task['timestamp']}')
    return failed_task
