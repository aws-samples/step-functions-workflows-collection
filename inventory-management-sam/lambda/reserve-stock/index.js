const { SFNClient, StartExecutionCommand } = require("@aws-sdk/client-sfn");

const client = new SFNClient();

exports.handler = async function(event, context) {
    for (const record of event.Records) {
        const order = JSON.parse(record.body);
        const params = {
            stateMachineArn: process.env.STATEMACHINE_ARN,
            name: `Order_${order.detail.orderId}`,
            input: JSON.stringify(order.detail)
        }  
        await client.send(new StartExecutionCommand(params));
    };
};