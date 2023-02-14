const { DynamoDB } = require('aws-sdk');
export {};

export const handler = async function(event:any) {
  console.log("request:", JSON.stringify(event, undefined, 2));

  let flightReservationID = hashIt(''+event.depart+event.arrive);
  console.log("flightReservationID:",flightReservationID)

  // Pass the parameter to fail this step 
  if(event.run_type === 'failFlightsReservation'){
      throw new Error('Failed to book the flights');
  }

  // create AWS SDK clients
  const dynamo = new DynamoDB();

  var params = {
      TableName: process.env.TABLE_NAME,
      Item: {
        'pk' : {S: event.trip_id},
        'sk' : {S: flightReservationID},
        'trip_id' : {S: event.trip_id},
        'id': {S: flightReservationID},
        'depart_city' : {S: event.depart_city},
        'depart_time': {S: event.depart_time},
        'arrive_city': {S: event.arrive_city},
        'arrive_time': {S: event.arrive_time},
        'transaction_status': {S: 'pending'}
      }
    };
  
  // Call DynamoDB to add the item to the table
  let result = await dynamo.putItem(params).promise().catch((error: any) => {
    throw new Error(error);
  });

  console.log('inserted flight reservation:');
  console.log(result);

 
  return {
    status: "ok",
    booking_id: flightReservationID
  }
};

function hashIt(s:string) {
  let myHash:any;

  for(let i = 0; i < s.length; i++){
    myHash = Math.imul(31, myHash) + s.charCodeAt(i) | 0;
  }

  return '' +Math.abs(myHash);
}