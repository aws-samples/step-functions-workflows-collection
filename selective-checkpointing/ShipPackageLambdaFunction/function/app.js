console.log('Loading function');
const { SFNClient, SendTaskSuccessCommand, SendTaskFailureCommand } = require('@aws-sdk/client-sfn');
const stepfunctions = new SFNClient({});

exports.lambdaHandler = async (event, context) => {

    await new Promise(resolve => setTimeout(resolve, Math.floor(Math.random() * 6000) + 1000));

       
    for (const record of event.Records) {
        const body = JSON.parse(record.body);
        
        console.log('body',body)
        const taskToken =body.TaskToken;

        const params = {
            output: "\"Callback task completed successfully.\"",
            taskToken: taskToken
        };
        console.log(`Calling Step Functions to complete callback task with params ${JSON.stringify(params)}`);
        try {
            let response = await stepfunctions.send(new SendTaskSuccessCommand(params));
        } catch (error) {
            let response = await stepfunctions.send(new SendTaskFailureCommand({"taskToken": taskToken, "error": "500", "cause": JSON.stringify(error)}));
            return { 'statusCode': 500,
                'body': {
                    'updated': true
                }
            }
    }
    }
    return { 'statusCode': 200,
                'body': {
                    'updated': true
                }
            }
}

