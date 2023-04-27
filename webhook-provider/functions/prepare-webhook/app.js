const crypto = require("crypto");
const { DynamoDBClient, PutItemCommand } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");

const dynamo = new DynamoDBClient(process.env.AWS_REGION);

const tableName = process.env.DASHBOARD_TABLE_NAME;
module.exports.lambdaHandler = async (event) => {
   
  
  
  const params = {
    TableName: tableName,
    Item: dataToWrite,
  };
  console.log(params);

  const docClient = DynamoDBDocumentClient.from(dynamo);

  try {
    const response = await docClient.send(new PutCommand(params));
    console.log(response);
  } catch (e) {
    console.error(e);
  }
 
  };
  