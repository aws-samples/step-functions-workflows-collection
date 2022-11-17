import { SecretsManagerClient, GetSecretValueCommand } from "@aws-sdk/client-secrets-manager"; // ES Modules import
import mysql from  "mysql2/promise";

const client = new SecretsManagerClient();
const input = { "SecretId": process.env.SECRET_NAME }
const command = new GetSecretValueCommand(input);
console.log('Retrieving secret during top-level await')
const secret = await client.send(command);

var rdsCredentials = JSON.parse(secret.SecretString);

console.log(process.env.AURORA_ENDPOINT)

const connection = await mysql.createConnection({
  host: process.env.AURORA_ENDPOINT,
  user: rdsCredentials.username,
  password: rdsCredentials.password,
  database: process.env.DB_NAME
});

console.log('Connected to MySQL')

export async function handler(event, context) {
  
  console.log("REQUEST RECEIVED:\n" + JSON.stringify(event));

  console.log('Creating Database Schema');
  
  try {
    console.log('Creating table orders');
    let [rows,fields] = await connection.query(` 
        CREATE TABLE orders( 
      	orderid VARCHAR(40) PRIMARY KEY,
      	orderstatus VARCHAR(255),
      	orderdate DATETIME
      )
    `);
    console.log('Table orders created successfully:', rows);
    
    console.log('Creating table orderitems');
    [rows,fields] = await connection.query(` 
      CREATE TABLE orderitems(
      	orderitemid BINARY(16) PRIMARY KEY,
      	itemid VARCHAR(40),
      	quantity SMALLINT,
      	orderid VARCHAR(40),
      	CONSTRAINT fk_order
          FOREIGN KEY (orderid) 
              REFERENCES orders(orderid)
      )
    `);
    console.log('Table orderitems created successfully:', rows);
       
    console.log('Creating procedure InsertOrder');
    [rows,fields] = await connection.query(` 
      CREATE PROCEDURE InsertOrder(
      	IN p_orderid VARCHAR(40),
      	IN p_orderstatus VARCHAR(255),
      	IN p_orderdate DATETIME
      )
      
      BEGIN
      
      INSERT INTO orders (orderid, orderstatus, orderdate)
      VALUES (p_orderid,p_orderstatus,p_orderdate);
      
      END
    `);
    console.log('Procedure InsertOrder created successfully:', rows);
       
    console.log('Creating procedure InsertOrderItem');
    [rows,fields] = await connection.query(` 
      CREATE PROCEDURE InsertOrderItem(
      	IN p_orderid VARCHAR(40),
      	IN p_itemid VARCHAR(40),
      	IN p_quantity SMALLINT
      )
      
      BEGIN
      
      INSERT INTO orderitems (orderitemid, orderid, itemid, quantity)
      VALUES (UUID_TO_BIN(UUID()), p_orderid, p_itemid, p_quantity);
      
      END
    `);
    console.log('Procedure InsertOrderItem created successfully:', rows);       
    
    console.log('Creating procedure GetItemReport');
    [rows,fields] = await connection.query(` 
      CREATE PROCEDURE GetItemReport()
      
      BEGIN
      
      SELECT a.itemid, SUM(a.quantity) as totalordered, DATE_FORMAT(MAX(b.orderdate),'%Y-%m-%d') as lastorderdate
      FROM orderitems a LEFT JOIN orders b ON a.orderid = b.orderid
      GROUP BY a.itemid;
      
      END
    `);
    console.log('Procedure GetItemReport created successfully:', rows);      
    
    console.log('Creating procedure GetMonthlyItemOrders');
    [rows,fields] = await connection.query(` 
      CREATE PROCEDURE GetMonthlyItemOrders(
      	IN p_itemid VARCHAR(40)
      )
      
      BEGIN
      
      SELECT DATE_FORMAT(b.orderdate,'%M %Y') as monthyear, SUM(a.quantity) as monthlyordered
      FROM orderitems a LEFT JOIN orders b ON a.orderid = b.orderid
      WHERE itemid = p_itemid
      GROUP BY year(b.orderdate),month(b.orderdate)
      ORDER BY b.orderdate DESC;
      
      END
    `);
    console.log('Procedure GetMonthlyItemOrders created successfully:', rows);

  }  
  catch (e){
       console.log('Error initializing database. : ' + JSON.stringify(e))
  }
}