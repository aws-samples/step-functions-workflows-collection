const { SFNClient, StartExecutionCommand } = require("@aws-sdk/client-sfn");

const client = new SFNClient();

exports.handler = async function(event, context) {
    for (const record of event.Records) {
        console.log(record);
        const params = {
            stateMachineArn: process.env.STATEMACHINE_ARN,
            name: `Check_Inventory_Level_${record.eventID}`,
            input: JSON.stringify(record.dynamodb.NewImage)
        }  
        await client.send(new StartExecutionCommand(params));
    }
}
