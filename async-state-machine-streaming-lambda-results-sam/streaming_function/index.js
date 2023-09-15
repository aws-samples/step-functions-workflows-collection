const { DynamoDBClient } = require ("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, UpdateCommand, QueryCommand } = require ("@aws-sdk/lib-dynamodb");

const max_lambda_remaining_time_ms = process.env.LambdaTimeoutBuffer; // max lambda execution time remaining before we finish
const dynamodb_polling_wait_ms = process.env.DDBPollingWaitMs; // wait time between calls to DDB
const final_result_fieldname = process.env.FinalResultFieldName; // name of the field in DDB that signifies the final result
const newLineString = '\n';

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

exports.handler = awslambda.streamifyResponse(
  async (event, responseStream, context) => {
  
  var finished = false; // controls the main execution loop until total_timeout is reached or final_result is received

  if (!event.queryStringParameters || !event.queryStringParameters.executionArn) {
    throw new Error("executionArn is a required query parameter");
  }

  const httpResponseMetadata = {
    statusCode: 200,
    headers: {
        "Content-Type": "text/plain"        
    }
  };

  responseStream = awslambda.HttpResponseStream.from(responseStream, httpResponseMetadata);

  executionArn = await formatExecutionArn(event.queryStringParameters.executionArn);
  
  while (!finished) {
    
    finished = await getWorkflowResultsAndStream(responseStream, executionArn);

    // make sure we have time to close the responseStream before lambda times out
    if (!finished && context.getRemainingTimeInMillis() < max_lambda_remaining_time_ms) {      
      finished = true;
    }
    
    // sleep interval between polling
    await new Promise(resolve => setTimeout(resolve, dynamodb_polling_wait_ms));
  }
  
  responseStream.end();
});

// extract the main identifiers from the ExecutionArn
async function formatExecutionArn(exeArn){
  decodedExeArn = decodeURIComponent(exeArn);
  splitExeArn = decodedExeArn.split(":");
  formattedExeArn = `${splitExeArn[6]}:${splitExeArn[7]}:${splitExeArn[8]}`;
  return formattedExeArn;
}

async function getWorkflowResultsAndStream(responseStream, executionArn){
  const response = await getResultItemsDDB(executionArn);
  
  if (response.Items && response.Items.length > 0){    
    const resultItems = response.Items;
    for (const result of resultItems) {            
      responseStream.write(result); 
      responseStream.write(newLineString);
      
      await setResultItemAsStreamedDDB(result.ExecutionArn, result.ResultTimestamp);

      if (final_result_fieldname in result){        
        return true;              
      }
    }
  }
  return false;
}

async function getResultItemsDDB(executionArn){
  const command = new QueryCommand({
    TableName: process.env.DDBTableName,
    KeyConditionExpression: "ExecutionArn = :ExecutionArn",
    FilterExpression: "attribute_not_exists(Streamed)",
    ExpressionAttributeValues: {
      ":ExecutionArn": executionArn
    },
    ConsistentRead: true,
  });

  var response;

  try
  {
    response = await docClient.send(command);
  } catch (e) {
    console.log("QueryCommand error", e);
  }
  return response;
}

async function setResultItemAsStreamedDDB(executionArn, resultTimestamp){
  const command = new UpdateCommand({
    TableName: process.env.DDBTableName,
    Key: {
      ExecutionArn: executionArn,
      ResultTimestamp: resultTimestamp
    },
    UpdateExpression: "set Streamed = :streamed",
    ExpressionAttributeValues: {
      ":streamed": true,
    },
    ReturnValues: "NONE",
  });

  try  
  {  
    await docClient.send(command);  
  } catch (e) {
    console.log("UpdateItem error", e);
  }
}

