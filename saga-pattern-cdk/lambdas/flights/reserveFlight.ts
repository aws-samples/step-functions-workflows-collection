// AWS SDK for JavaScript v3 is provided by the nodejs24.x Lambda runtime
const { DynamoDBClient, PutItemCommand } = require('@aws-sdk/client-dynamodb');
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
  const dynamo = new DynamoDBClient({});

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
  let result = await dynamo.send(new PutItemCommand(params)).catch((error: any) => {
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