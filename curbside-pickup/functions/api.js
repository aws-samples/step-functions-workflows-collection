const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, ScanCommand } = require("@aws-sdk/lib-dynamodb");
const { SFNClient, SendTaskSuccessCommand, StartExecutionCommand } = require("@aws-sdk/client-sfn");
const DDB = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const stepfunctions = new SFNClient({});

// Env Vars
const { TABLE_NAME, STATEMACHINE_ARN } = process.env;

const buildRes = async (data, status) => {
    return {
        statusCode: status,
        headers: {
            "Access-Control-Allow-Headers" : "Content-Type",
            "Access-Control-Allow-Origin": "*", // Allow from anywhere 
            "Access-Control-Allow-Methods": "*" // Allow all request methods
        },
        body: JSON.stringify(data)
    }

}

const getDDB = async () => {
    // get all data from dynamodb table
    const { $metadata, ...res } = await DDB.send(new ScanCommand({ TableName: TABLE_NAME }))
    console.log('DDB RES:', res)
    return res;
}

const postTaskToken = async (body) => {
    const { id, taskToken, location, taskComplete } = body == null ? {} : JSON.parse(body)
    // Send Task Success or Fail to Stepfunctions
    // Check for null
    if (id == null || taskToken == null || taskComplete == null) throw 'Error: id, taskToken, taskComplete and location are mandatory items'

    const params = {
        output: JSON.stringify({id: id, taskComplete, location}),
        taskToken: taskToken,
    }
    console.log('Task Params -- ', params) 
    await stepfunctions.send(new SendTaskSuccessCommand(params))
    return 'TASK-SUCCESS'; 
}

const postOrder = async (body) => {
    // Start State Machine Execution and Pass Body
    const params = {
        stateMachineArn: STATEMACHINE_ARN,
        input: body
    }
    await stepfunctions.send(new StartExecutionCommand(params))
    return 'ORDER-SUCCESS';
}





exports.handler = async (event) => {
    try {
        console.log('EVENT:', event)
        const {httpMethod, path, queryStringParameters, body}= event

        let res = 'SUCCESS'

        // Route to Business Logic
        // Scan DDB for all Data
        if (path === '/ddb') res = await getDDB()
        // Customer has Arrived && Post TaskToken to Statemachine
        if (path === '/task-complete') res = await postTaskToken(body)
        // Customer has Arrived && Post TaskToken to Statemachine
        if (path === '/order') res = await postOrder(body)

        return await buildRes(res, 200); 
    }
    catch (err) {
        console.error(err)
        return await buildRes(err, 400)
    }       
};