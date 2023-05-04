const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");
const { KMSClient, EncryptCommand } = require("@aws-sdk/client-kms");

const dynamo = new DynamoDBClient(process.env.AWS_REGION);
const docClient = DynamoDBDocumentClient.from(dynamo);

const tableName = process.env.WEBHOOK_TABLE;

const kmsKeyId = process.env.KMS_KEY;
const kms = new KMSClient(process.env.AWS_REGION);

exports.lambdaHandler = async (event, context) => {
  const kmsparams = {
    KeyId: kmsKeyId,
    Plaintext: Buffer.from(event.signingToken),
  };
  console.log(kmsparams);
  console.log(event);

  const command = new EncryptCommand(kmsparams);
  var token = await kms.send(command);
  //ciphertextBlob is Uint8Array, convert to base64 encoded
  token = Buffer.from(token.CiphertextBlob).toString("base64");

  const params = {
    TableName: tableName,
    Item: {
      pk: event.pk,
      type: event.type,
      signingToken: token,
      url: event.url,
    },
  };
 
  try {
    const response = await docClient.send(new PutCommand(params));
    
    return { statusCode: 200, body: "Item saved to DynamoDB" };
  } catch (err) {
    console.error("Error saving to DynamoDB:", err);
    return { statusCode: 500, body: "Error saving to DynamoDB" };
  }
};
