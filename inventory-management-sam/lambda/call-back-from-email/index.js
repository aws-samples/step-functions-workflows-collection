const { SFNClient, SendTaskSuccessCommand } = require("@aws-sdk/client-sfn");

const client = new SFNClient();

exports.handler = async function(event, context) {
    const action = event.queryStringParameters.action;
    const taskToken = event.queryStringParameters.taskToken;

    if (action === "approve") {
        const message = { "Status": "Approved" };
        const input = { 
            taskToken: taskToken,
            output: JSON.stringify(message)
        };
        const command = new SendTaskSuccessCommand(input);
        await client.send(command);
    } else if (action === "reject") {     
        const message = { "Status": "Rejected" };
            
        const input = { 
            taskToken: taskToken,
            output: JSON.stringify(message)
        };
        const command = new SendTaskSuccessCommand(input);
        await client.send(command);
    } else {
        const errorMessage = "Unrecognized action. Expected: approve, reject."
        console.error(errorMessage);
        return errorMessage;
        
    }
    return "Thank you for your respose!"
    
}              