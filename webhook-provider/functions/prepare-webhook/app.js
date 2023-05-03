const { createHmac } = require("crypto");
const crypto = require("crypto");
const { DynamoDBClient, PutItemCommand } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");

const dynamo = new DynamoDBClient(process.env.AWS_REGION);
const docClient = DynamoDBDocumentClient.from(dynamo);
const tableName = process.env.WEBHOOK_TABLE;
const encoder = new TextEncoder();
const kmsKeyId = process.env.KMS_KEY;

// Decrypt the signing token using the KMS key
const decryptSigningToken = async (encryptedData, keyId) => {
  const params = {
    CiphertextBlob: Buffer.from(encryptedData, "base64"),
    KeyId: keyId,
  };

  try {
    const { plaintext } = await kms.decrypt(params).promise();
    return plaintext.toString();
  } catch (error) {
    console.error("Decryption failed:", error);
    throw error;
  }
};

/**
 * Lambda function for processing webhook events and storing data in DynamoDB.
 * @param {object} event - The event object triggered by the Lambda invocation.
 * @returns {object} - An object containing information about the stored data.
 */
module.exports.lambdaHandler = async (event) => {
  let webhookInfo = JSON.parse(JSON.stringify(event.webhookData.Item));
  let currentTime = new Date().toUTCString();
  let payload = event.detail;

  //Decrypt the signing Token
  var signingToken = event.webhookData.Item.signingToken.S;
  if (typeof signingToken === "string" && signingToken.length === 0) {
    throw new Error("signing token is empty");
  }
  var decryptedSigningToken = await decryptSigningToken(signingToken, kmsKeyId);

  // Generate a token for the payload
  let token = createHmac("sha256", encoder.encode(decryptedSigningToken))
    .update(encoder.encode(JSON.stringify(payload)))
    .digest("hex");

  // Create the DynamoDB record for the webhook call.

  let postData = {
    pk: webhookInfo.pk.S + "+" + payload.id + "+" + crypto.randomUUID(),
    type: "webhookcall",
    url: webhookInfo.url.S,
    payload: payload,
    invokeTime: currentTime,
    status: "pending",
    token: token,
    messageTime: event.time,
  };

  const params = {
    TableName: tableName,
    Item: postData,
  };

  const response = await docClient.send(new PutCommand(params));
  // Return the data to the SFN to map to the next step.
  return {
    id: postData.pk,
    payload: postData.payload,
    url: postData.url,
    token: token,
  };
};
