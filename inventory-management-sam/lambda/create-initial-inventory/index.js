const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");
const response = require("cfn-response");
const { v4 } = require('uuid');

const dynamo = new DynamoDBClient(process.env.AWS_REGION);
const docClient = DynamoDBDocumentClient.from(dynamo);
const products = [ 
    { id: v4(), name: 'tv', stock: 10, threshold: 2, status: "IN STOCK", minPOAmount: 10 },
    { id: v4(), name: 'laptop', stock: 20, threshold: 5, status: "IN STOCK", minPOAmount: 15 },
    { id: v4(), name: 'keyboard', stock: 30, threshold: 10, status: "IN STOCK", minPOAmount: 20 },
    { id: v4(), name: 'mouse', stock: 50, threshold: 15, status: "IN STOCK", minPOAmount: 30 },
    { id: v4(), name: 'monitor', stock: 25, threshold: 4, status: "IN STOCK", minPOAmount: 10 },
    { id: v4(), name: 'desk', stock: 100, threshold: 20, status: "IN STOCK", minPOAmount: 40 },
    { id: v4(), name: 'chair', stock: 40, threshold: 12, status: "IN STOCK", minPOAmount: 30 }
]

exports.handler = function(event, context) {
    console.log(JSON.stringify(event,null,2));
    const tableName = event.ResourceProperties.DynamoTableName
    try {
        products.forEach(async (product) => {
       
            const params = {
                TableName: tableName,
                Item: product
            }
            await docClient.send(new PutCommand(params));
            
        })
    } catch {
        response.send(event, context, "FAILED", {});
    } 
    response.send(event, context, "SUCCESS", {});
};