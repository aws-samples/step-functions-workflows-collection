import { SecretsManagerClient, GetSecretValueCommand } from "@aws-sdk/client-secrets-manager"; // ES Modules import
import { unmarshall } from "@aws-sdk/util-dynamodb";
import mysql from  "mysql2/promise";
const client = new SecretsManagerClient();
const input = { "SecretId": process.env.SECRET_NAME }
const command = new GetSecretValueCommand(input);
console.log('Retrieving secret during top-level await')
const secret = await client.send(command);

var rdsCredentials = JSON.parse(secret.SecretString);

console.log(process.env.AURORA_ENDPOINT)

const connection = await mysql.createPool({
  host: process.env.AURORA_ENDPOINT,
  user: rdsCredentials.username,
  password: rdsCredentials.password,
  database: process.env.DB_NAME
});

console.log('Connected to MySQL')

export async function handler(event, context, callback) {

  try {

        await Promise.all(event.Records.map(async (record) => {
            console.log('Stream record: ', JSON.stringify(record, null, 2));
            if (record.eventName == 'INSERT') {
                var obj = unmarshall(record.dynamodb.NewImage);
                console.log('Processing order with id: ', obj.orderid);

                const [rows,fields] = await connection.query('CALL InsertOrder(?, ?, ?)',
                    [
                        obj.orderid,
                        obj.status,
                        obj.lastUpdateDate
                    ]
                );
                console.log('orders insert result: ', rows);
                
                await Promise.all(obj.items.map(async (item) => {
                    console.log(obj.orderid, item.itemid, item.quantity);
                    const [rows,fields] = await connection.query('CALL InsertOrderItem(?, ?, ?)',
                        [
                            obj.orderid,
                            item.itemid,
                            item.quantity
                        ]
                    );                    
                }));
            }   
        }));
      
        const response = {
           statusCode: 200,
           body: `Processed ${event.Records.length} records.`
       };
       return response;
  
  }
  catch (e){
        const response = {
           statusCode: 500,
           body: 'Error porcessing records. : ' + JSON.stringify(e)
       };
       return response;      
  }

}
