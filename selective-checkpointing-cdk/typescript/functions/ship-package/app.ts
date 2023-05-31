var AWS = require('aws-sdk');
var stepfunctions = new AWS.StepFunctions({apiVersion: '2016-11-23'});

exports.lambdaHandler = async (event: { Records: any; }, context: any, callback: any) => {

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
            let response = await stepfunctions.sendTaskSuccess(params).promise();
        } catch (error) {
            let response = await stepfunctions.sendTaskFailure({
                "taskToken": taskToken,
                "error": 500,
                "cause": JSON.stringify(error)
            }).promise();
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

