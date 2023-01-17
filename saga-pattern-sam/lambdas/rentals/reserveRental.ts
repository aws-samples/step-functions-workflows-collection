const { DynamoDB } = require('aws-sdk');
export {};

export const handler = async function(event:any) {
  console.log("request:", JSON.stringify(event, undefined, 2));

  let carRentalReservationID = hashIt(''+event.rental_from+event.rental_to);
  console.log("carReservationID:",carRentalReservationID)

  // Pass the parameter to fail this step 
  if(event.run_type === 'failCarRentalReservation'){
      throw new Error('Failed to book the car rental');
  }

  // create AWS SDK clients
  const dynamo = new DynamoDB();

  var params = {
      TableName: process.env.TABLE_NAME,
      Item: {
        'pk' : {S: event.trip_id},
        'sk' : {S: carRentalReservationID},
        'trip_id' : {S: event.trip_id},
        'id': {S: carRentalReservationID},
        'rental': {S: event.rental},
        'rental_from': {S: event.rental_from},
        'rental_to': {S: event.rental_to},
        'transaction_status': {S: 'pending'}
      }
    };
  
  // Call DynamoDB to add the item to the table
  let result = await dynamo.putItem(params).promise().catch((error: any) => {
    throw new Error(error);
  });

  console.log('inserted car rental reservation:');
  console.log(result);

 
  return {
    status: "ok",
    booking_id: carRentalReservationID
  }
};

function hashIt(s:string) {
  let myHash:any;

  for(let i = 0; i < s.length; i++){
    myHash = Math.imul(31, myHash) + s.charCodeAt(i) | 0;
  }

  return ''+Math.abs(myHash);
}