// SDK v3 is provided by the Lambda runtime, so it is loaded with require and not listed in package.json.
const { SFNClient, SendTaskSuccessCommand, SendTaskFailureCommand } = require('@aws-sdk/client-sfn');

const stepfunctions = new SFNClient({});

export const lambdaHandler = async (event: { Records: any; }, context: any) => {

    await new Promise(resolve => setTimeout(resolve, Math.floor(Math.random() * 6000) + 1000));


    for (const record of event.Records) {
        const body = JSON.parse(record.body);

        const taskToken = body.TaskToken;

        const params = {
            output: "\"Callback task completed successfully.\"",
            taskToken: taskToken
        };

        // console.log(`Calling Step Functions to complete callback task with params ${JSON.stringify(params)}`);
        try {
            let response = await stepfunctions.send(new SendTaskSuccessCommand(params));
        } catch (error) {
            let response = await stepfunctions.send(new SendTaskFailureCommand({
                "taskToken": taskToken,
                "error": "500",
                "cause": JSON.stringify(error)
            }));
            return {
                'statusCode': 500,
                'body': {
                    'updated': true
                }
            }
        }
    }
    return {
        'statusCode': 200,
        'body': {
            'updated': true
        }
    }
}

