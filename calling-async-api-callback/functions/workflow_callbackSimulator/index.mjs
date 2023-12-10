
import { SFNClient, SendTaskSuccessCommand, SendTaskFailureCommand } from "@aws-sdk/client-sfn";
  
const AWS_REGION = process.env.AWS_REGION_ID;

const client = new SFNClient({ region: AWS_REGION });



export async function handler(event) {
    console.log(event);
    const payload = event.payload;
    const taskToken = event.taskToken;
    
    var input = {};
    var apiResponse = {};
    var command = {};
    if(payload.status == "success"){
      apiResponse = {status:200, payload:{body:"sample sucess message"}};
      input = {
        output: JSON.stringify(apiResponse), /* required */
        taskToken: JSON.stringify(taskToken) /* required */
      };
      command = new SendTaskSuccessCommand(input);
    } else {
      input = {
        taskToken: JSON.stringify(taskToken), /* required */
        cause: "sample error message", /* optional */
        error: "sample error message" /* optional */
      };
      command = new SendTaskFailureCommand(input);
    }
    const response = await client.send(command);
    console.log(response);
    }
  