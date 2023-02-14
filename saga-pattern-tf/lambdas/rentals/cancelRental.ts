const { DynamoDB } = require('aws-sdk');
export {};

export const handler = async function(event:any) {
  console.log("request:", JSON.stringify(event, undefined, 2));


  let reservationID = '';
  if (typeof event.ReserveCarRentalResult !== 'undefined') {
    reservationID = event.ReserveCarRentalResult.Payload.booking_id;
  }


  const dynamo = new DynamoDB();

  var params = {
    TableName: process.env.TABLE_NAME,
    Key: {
      'pk' : {S: event.trip_id},
      'sk' : {S: 'CAR#'+reservationID}
    }
  };
  
  // Call DynamoDB to delete the item from the table
  let result = await dynamo.deleteItem(params).promise().catch((error: any) => {
    throw new Error(error);
  });

  console.log('deleted car rental  reservation:');
  console.log(result);


  return {status: "ok"}
};