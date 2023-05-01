const { createHmac } = require("crypto");
const crypto = require("crypto");
const { DynamoDBClient, PutItemCommand } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");

const dynamo = new DynamoDBClient(process.env.AWS_REGION);
const docClient = DynamoDBDocumentClient.from(dynamo);
const tableName = process.env.WEBHOOK_TABLE;
const encoder = new TextEncoder();

module.exports.lambdaHandler = async (event) => {
  console.log(event);
  let callInfo = JSON.parse(JSON.stringify(event.webhookData.Item));
  let currentTime = new Date().toUTCString();
  let payload = event.detail;
  console.log(callInfo);
  console.log(payload);
  let token = createHmac("sha256", encoder.encode(callInfo.signingToken.S))
    .update(encoder.encode(JSON.stringify(payload)))
    .digest("hex");

  let postData = {
    pk: callInfo.pk.S + "+" + payload.id + "+" + crypto.randomUUID(),
    type: "webhookcall",
    url: callInfo.url.S,
    payload: payload,
    invokeTime: currentTime,
    status: "pending",
    token: token,
    messageTime: event.time,
  };
  console.log(postData);
  const params = {
    TableName: tableName,
    Item: postData,
  };
  console.log(params);

  try {
    const response = await docClient.send(new PutCommand(params));
    console.log(response);
    return {
      id: postData.pk,
      payload: postData.payload,
      url: postData.url,
      token: token,
    };
  } catch (e) {
    console.error(e);
  }
};