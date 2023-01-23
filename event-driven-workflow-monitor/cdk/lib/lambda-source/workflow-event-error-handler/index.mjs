import { SFNClient, SendTaskFailureCommand } from "@aws-sdk/client-sfn"; // SFN Modules import
import { DynamoDBClient, GetItemCommand, DeleteItemCommand } from "@aws-sdk/client-dynamodb"; // DDB Modules import

export const handler = async (event, context, callback) => {
  console.log("--> Received event from EventBridge:");
  console.log(event);
  const ddbclient = new DynamoDBClient();
  const workflowkey = await event.detail.workflowkey;
  const tableName = process.env.TABLENAME;

  // Retrieve the task token from DynamoDB and fail the monitoring task in the associated step function instance
  const paramsddb = {
    TableName: tableName,
    Key: {
      'workflowkey': { S: workflowkey }
    },
    ProjectionExpression: 'tasktoken'
  };

  try {
    const commandddb = new GetItemCommand(paramsddb);
    const responseddb = await ddbclient.send(commandddb);
    console.log("--> Retrieved task token from DynamoDB:");
    console.log(responseddb);
    const taskresponse = await sendTaskFailure(responseddb['Item']['tasktoken']['S']);
  }
  catch (error) {
    console.log(error);
    return (error);
  }

  //Delete DynamoDB entry if above failure command was sent successfully
  try {
    const deletecommanddb = new DeleteItemCommand(paramsddb);
    const deleteresponse = await ddbclient.send(deletecommanddb);
    console.log("--> DynamoDB item deleted.");
    console.log(deleteresponse);
    return (deleteresponse);
  }
  catch (error) {
    console.log(error);
    return (error);
  }
};

async function sendTaskFailure(tasktoken) {
  const sfnclient = new SFNClient();
  try {
    const stopmonitoringparams = {
      cause: "\"Error detected.\"",
      error: "\"Some error.\"",
      taskToken: tasktoken
    };
    const commandstopmon = new SendTaskFailureCommand(stopmonitoringparams);
    const responsestopmon = await sfnclient.send(commandstopmon);
    console.log("--> Task failure command sent.");
    return (responsestopmon);
  }
  catch (error) {
    console.log(error);
    return (error);
  }
}