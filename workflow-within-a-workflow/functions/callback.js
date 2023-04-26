console.log('Loading function');
const AWS = require('aws-sdk');
exports.lambda_handler = (event, context, callback) => {
    console.log('event ' + JSON.stringify(event));
    console.log('context ' + JSON.stringify(context));

    const taskToken = event.TaskToken;
    const message = event.Message;

    const params = {
        taskToken: taskToken,
        output: "\"" + message + "\""
    }

    const stepfunctions = new AWS.StepFunctions();
    stepfunctions.sendTaskSuccess(params, function (err, data) {
        if (err) {
            console.log("Error", err);
            callback(null, err)
        } else {
            console.log("Success", data);
            callback(null);
        }
    });
}