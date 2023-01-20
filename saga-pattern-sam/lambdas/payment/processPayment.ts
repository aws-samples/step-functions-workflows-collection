const { DynamoDB } = require('aws-sdk');
export {};

export const handler = async function(event:any) {
  console.log("request:", JSON.stringify(event, undefined, 2));

  let flightReservationID = '';
  if (typeof event.ReserveFlightResult !== 'undefined') {
    flightReservationID = event.ReserveFlightResult.Payload.booking_id;
  }

  let carReservationID = '';
  if (typeof event.ReserveCarRentalResult !== 'undefined') {
    flightReservationID = event.ReserveCarRentalResult.Payload.booking_id;
  }


  let paymentID = hashIt(''+flightReservationID+carReservationID);

  // Pass the parameter to fail this step 
  if(event.run_type === 'failPayment'){
    throw new Error('Failed to process payment');
  }

  // create AWS SDK clients
  const dynamo = new DynamoDB();

  var params = {
      TableName: process.env.TABLE_NAME,
      Item: {
        'pk' : {S: event.trip_id},
        'sk' : {S: paymentID},
        'trip_id' : {S: event.trip_id},
        'id': {S: paymentID},
        'amount': {S: "750.00"},
        'currency': {S: "USD"},
        'transaction_status': {S: "confirmed"}
      }
    };
  
  // Call DynamoDB to add the item to the table
  let result = await dynamo.putItem(params).promise().catch((error: any) => {
    throw new Error(error);
  });

  console.log('Payment Processed Successfully:');
  console.log(result);

  // return status of ok
  return {
    status: "ok",
    payment_id: paymentID
  }
};

function hashIt(s:string) {
  let myHash:any;

  for(let i = 0; i < s.length; i++){
    myHash = Math.imul(31, myHash) + s.charCodeAt(i) | 0;
  }

  return ''+Math.abs(myHash);
}