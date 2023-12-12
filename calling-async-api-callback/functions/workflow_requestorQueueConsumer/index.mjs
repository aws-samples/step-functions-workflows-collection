import { SFNClient, StartExecutionCommand } from "@aws-sdk/client-sfn";

// Get environment variables
const STATE_MACHINE_ARN = process.env.STATE_MACHINE_ARN;
const AWS_REGION = process.env.AWS_REGION_ID;

// Validate required env vars 
if (!STATE_MACHINE_ARN) {
  throw new Error("State machine ARN not provided");
}

if(!AWS_REGION) {
  throw new Error("AWS Region not provided");  
}

// SDK client
const sfnClient = new SFNClient({ region: AWS_REGION });

export const handler = async (event) => {

    for (const record of event.Records) {  
    
        const input = record.body;
        
        const command = new StartExecutionCommand({
            stateMachineArn: STATE_MACHINE_ARN,
             input: input  
        });
   
        const response = await sfnClient.send(command);
        
        // Log response 
        console.log("Step Function response", response);
        
    }
  
};