console.log('Loading function');
var AWS = require('aws-sdk');
var stepfunctions = new AWS.StepFunctions({apiVersion: '2016-11-23'});

exports.lambdaHandler = async(event, context, callback) => {

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
            let response = await stepfunctions.sendTaskSuccess(params).promise();
        } catch (error) {
            let response = await stepfunctions.sendTaskFailure({"taskToken": taskToken, "error":500,"cause":error}).promise();
            return { 'statusCode': 500,
                'body': {
                    'updated': True
                }
            }
    }
    }
    return { 'statusCode': 200,
                'body': {
                    'updated': True
                }
            }
}

