const aws = require('aws-sdk');
const docClient = new aws.DynamoDB.DocumentClient();
var stepfunctions = new aws.StepFunctions()


const SF_ARN = process.env.SF_ARN;
const TABLE_NAME = process.env.TABLE_NAME;


exports.handler = async (event, context) => {
    try {
        const today = getDate();

        console.log(`request received, fetching events for: ${today}`);

        const data = await queryItems(today);

        console.log(`todays events are: ${JSON.stringify(data.Items)}`);

        const todaysEvents = data.Items;

        if (todaysEvents && todaysEvents.length > 0) {
            console.log("length is more than 0, trigger Step Function");
            for (const event of todaysEvents) {
                await triggerStepFunction(event);

            }
        } else {
            console.log("there are no events for today");
        }
        return {
            message: "Successfully retrieved today's events",
        };
    } catch (err) {
        return {
            error: err,
        };
    }
};


async function triggerStepFunction(event) {
    console.log("trigger step function");
    const params = {
        stateMachineArn: SF_ARN,
        input: JSON.stringify(event),
    };

    return await stepfunctions.startExecution(params).promise();
}

function getDate() {
    const date_ob = new Date();
    const day = ("0" + date_ob.getDate()).slice(-2);
    const month = ("0" + (date_ob.getMonth() + 1)).slice(-2);
    const year = date_ob.getFullYear();
    const today = `${year}-${month}-${day}`;
    return today;
}

async function queryItems(today) {

    const ddb_params = {
        TableName: TABLE_NAME,
        KeyConditionExpression: "eventDate = :today",
        ExpressionAttributeValues: {
            ":today": today,

        }
    };
    try {
        const data = await docClient.query(ddb_params).promise();
        return data;
    } catch (err) {
        console.error(
            `error querying for todays events with query: ${JSON.stringify(
                ddb_params
            )}`
        );
        throw err;
    }
}



