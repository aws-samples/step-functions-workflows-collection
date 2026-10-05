console.log('Loading function');
const { SFNClient, SendTaskSuccessCommand } = require('@aws-sdk/client-sfn');
const stepfunctions = new SFNClient();

exports.lambda_handler = async (event, context) => {
    console.log('event ' + JSON.stringify(event));
    console.log('context ' + JSON.stringify(context));

    const taskToken = event.TaskToken;
    const message = event.Message;

    const params = {
        taskToken: taskToken,
        output: "\"" + message + "\""
    }

    try {
        const data = await stepfunctions.send(new SendTaskSuccessCommand(params));
        console.log("Success", data);
        return;
    } catch (err) {
        console.log("Error", err);
        return err;
    }
}
