import { SFNClient, SendTaskSuccessCommand } from "@aws-sdk/client-sfn";
import { DynamoDBClient, GetItemCommand, DeleteItemCommand } from "@aws-sdk/client-dynamodb";

export const handler = async (event, context, callback) => {
  console.log("--> Received event from EventBridge:");
  console.log(event);
  const ddbclient = new DynamoDBClient();
  const sfnclient = new SFNClient();
  const workflowkey = await event.detail.workflowkey;

  // Retrieve the task token from DynamoDB
  // Complete the monitoring task in the associated step function instance
  // Complete the monitoring shutdown task in the associated step function instance
  const paramsddb = {
    TableName: process.env.TABLENAME,
    Key: {
      'workflowkey': { S: workflowkey }
    },
    ProjectionExpression: 'tasktoken',
  };
  try {
    const getcommandddb = new GetItemCommand(paramsddb);
    const workflowitem = await ddbclient.send(getcommandddb);
    console.log("--> Retrieved token from DynamoDB:");
    console.log(workflowitem);
    // Send task success command to monitoring task
    const tasksuccess1 = await sendTaskSuccess(sfnclient, workflowitem['Item']['tasktoken']['S']);
    // Send task success command to EventBridge PutItem task which led to the invocation of this Lambda function
    const tasksuccess2 = await sendTaskSuccess(sfnclient, event.detail.tasktoken);
  }
  catch (error) {
    console.log(error);
    return (error);
  }

  //Delete DynamoDB entry if above success commands were sent successfully
  try {
    const deletecommanddb = new DeleteItemCommand(paramsddb);
    const deleteresponse = await ddbclient.send(deletecommanddb);
    console.log("--> DynamoDB item deleted:");
    console.log(deleteresponse);
  }
  catch (error) {
    return (error);
  }
};

async function sendTaskSuccess(sfnclient, tasktoken) {
  try {
    const stopmonitoringparams = {
      output: "\"Monitoring task stopped successfully.\"",
      taskToken: tasktoken
    };
    const commandstopmon = new SendTaskSuccessCommand(stopmonitoringparams);
    const responsestopmon = await sfnclient.send(commandstopmon);
    console.log("--> Task success command sent with token:");
    console.log(tasktoken);
    return (responsestopmon);
  }
  catch (error) {
    console.log(error);
    return (error);
  }
}
