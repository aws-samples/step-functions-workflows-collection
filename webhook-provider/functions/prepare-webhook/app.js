const { createHmac, randomUUID } = require("crypto");

const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");
const { KMSClient, DecryptCommand } = require("@aws-sdk/client-kms");

const dynamo = new DynamoDBClient(process.env.AWS_REGION);
const docClient = DynamoDBDocumentClient.from(dynamo);
const tableName = process.env.WEBHOOK_TABLE;
const encoder = new TextEncoder();
const kmsKeyId = process.env.KMS_KEY;
const kms = new KMSClient(process.env.AWS_REGION);

// Decrypt the signing token using the KMS key
const decryptSigningToken = async (encryptedData, keyId) => {
  //param ciphertextBlob for decrypt should be Uint8Array

  const buffer = Buffer.from(encryptedData, "base64");
  const uint8Array = Uint8Array.from(buffer);
  const params = {
    CiphertextBlob: uint8Array,
    KeyId: keyId,
  };

  try {
    const command = new DecryptCommand(params);
    const plainText = await kms.send(command);
    //plaintext is also Uint8Array - convert to string
    return Buffer.from(plainText.Plaintext).toString();
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
  var callbackURL = webhookInfo.url.S;

  // validate the payload and callback url
  if (typeof payload === "undefined") {
    throw new Error("payload is empty");
  }

  if (typeof callbackURL === "string" && callbackURL.length === 0) {
    throw new Error("call back urlis empty");
  }

  var signingToken = event.webhookData.Item.signingToken.S;

  //Decrypt the signing Token
  var decryptedSigningToken = await decryptSigningToken(signingToken, kmsKeyId);

  // Generate a signature token for the payload
  let token = createHmac("sha256", encoder.encode(decryptedSigningToken))
    .update(encoder.encode(JSON.stringify(payload)))
    .digest("hex");

  // Create the DynamoDB record for the webhook call.

  let postData = {
    pk: webhookInfo.pk.S + "+" + payload.id + "+" + randomUUID(),
    type: "webhookcall",
    url: callbackURL,
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
  try {
    const response = await docClient.send(new PutCommand(params));

    return {
      id: postData.pk,
      payload: postData.payload,
      url: postData.url,
      token: token,
    };
  } catch (err) {
    console.error("Error saving to DynamoDB:", err);
    throw err;
  }
};
