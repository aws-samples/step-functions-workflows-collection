// AWS SDK for JavaScript v3 is provided by the nodejs24.x Lambda runtime
const { DynamoDBClient, DeleteItemCommand } = require('@aws-sdk/client-dynamodb');
export {};

export const handler = async function(event:any) {
  console.log("request:", JSON.stringify(event, undefined, 2));


  let reservationID = '';
  if (typeof event.ReserveCarRentalResult !== 'undefined') {
    reservationID = event.ReserveCarRentalResult.Payload.booking_id;
  }


  const dynamo = new DynamoDBClient({});

  var params = {
    TableName: process.env.TABLE_NAME,
    Key: {
      'pk' : {S: event.trip_id},
      'sk' : {S: 'CAR#'+reservationID}
    }
  };
  
  // Call DynamoDB to delete the item from the table
  let result = await dynamo.send(new DeleteItemCommand(params)).catch((error: any) => {
    throw new Error(error);
  });

  console.log('deleted car rental  reservation:');
  console.log(result);


  return {status: "ok"}
};