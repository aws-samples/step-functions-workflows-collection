const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, ScanCommand } = require("@aws-sdk/lib-dynamodb");
const { EventBridgeClient, PutEventsCommand } = require("@aws-sdk/client-eventbridge");
const { v4 } = require('uuid');

const dynamo = new DynamoDBClient(process.env.AWS_REGION);
const docClient = DynamoDBDocumentClient.from(dynamo);
const ebClient = new EventBridgeClient()
const tableName = process.env.INVENTORY_TABLE
const min = 1;
const max = 200;
exports.handler = async function (event, context) {
  const products = await docClient.send(new ScanCommand({ TableName: tableName }));
  // select a random product
  const product = products.Items[Math.floor(Math.random() * products.Items.length)];
  const order = {
    orderId: v4(),
    productId: product.id,
    quantity: Math.floor(Math.random() * (max - min + 1) + min)
  }

  const input = {
    Entries: [
      {
        Time: new Date(),
        Source: "com.orders",
        DetailType: "new-order-received",
        Detail: JSON.stringify(order),
        EventBusName: process.env.EVENTBUS_NAME
      },
    ]
  };
  const command = new PutEventsCommand(input);
  await ebClient.send(command);
  return "new-order-received event sent : " + JSON.stringify(order);

};