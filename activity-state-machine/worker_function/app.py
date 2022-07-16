import json
import boto3

client = boto3.client('stepfunctions')

def lambda_handler(event, context):
    
    #List all the activities
    activities_list = client.list_activities()

    #Fetch activity ARN for the activity created
    for activity in activities_list['activities'] :
        if activity['name'] == 'TestActivity':
            activity_Arn = activity['activityArn']
            break

    #Poll Step Functions by using GetActivityTask, and sending the ARN for the related activity
    activity_tasktoken = client.get_activity_task(activityArn=activity_Arn,workerName='LambdaWorker')

    #print(activity_tasktoken['taskToken'])
    output_json = {"Result": "value"}

    #After the activity worker completes its work, provide a report of its success or failure 
    send_task_success_response = client.send_task_success(taskToken=activity_tasktoken['taskToken'], output= json.dumps(output_json))
    
    print(send_task_success_response)

    return {
        'statusCode': 200,
        'body': json.dumps('Worker implementaion successfully completed!')
    }

