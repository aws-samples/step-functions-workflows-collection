import { SecretsManagerClient, GetSecretValueCommand } from "@aws-sdk/client-secrets-manager"; // ES Modules import
import mysql from  "mysql2/promise";
const client = new SecretsManagerClient();
const input = { "SecretId": process.env.SECRET_NAME }
const command = new GetSecretValueCommand(input);
console.log('Retrieving secret during top-level await')
const secret = await client.send(command);

var rdsCredentials = JSON.parse(secret.SecretString);

console.log(process.env.AURORA_ENDPOINT)

const connection = await mysql.createPool({
  connectionLimit: 10,
  host: process.env.AURORA_ENDPOINT,
  user: rdsCredentials.username,
  password: rdsCredentials.password,
  database: process.env.DB_NAME
});

console.log('Connected to MySQL')

export async function handler(event, context) {
  let response = null;
  
   console.log('Processing order with id: ', event.itemid);
  const [rows,fields] = await connection.query('CALL GetMonthlyItemOrders(?)',event.itemid);
  console.log(rows,fields);

  response = {
    statusCode: 200,
    body: rows[0],
  };
  return response;
}