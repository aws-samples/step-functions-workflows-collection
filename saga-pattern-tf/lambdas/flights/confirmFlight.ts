// AWS SDK for JavaScript v3 is provided by the nodejs24.x Lambda runtime
const { DynamoDBClient, UpdateItemCommand } = require('@aws-sdk/client-dynamodb');
export {};

export const handler = async function(event:any) {
  console.log("request:", JSON.stringify(event, undefined, 2));

  // Pass the parameter to fail this step 
  if(event.run_type === 'failFlightsConfirmation'){
      throw new Error('Failed to book the flights');
  }

  let reservationID = '';
  if (typeof event.ReserveFlightResult !== 'undefined') {
    reservationID = event.ReserveFlightResult.Payload.booking_id;
  }

  const dynamo = new DynamoDBClient({});

  var params  = {
    TableName: process.env.TABLE_NAME,
    Key: {
      'pk' : {S: event.trip_id},
      'sk' : {S: 'FLIGHT#'+reservationID}
    },
    "UpdateExpression": "set transaction_status = :booked",
    "ExpressionAttributeValues": {
        ":booked": {"S": "confirmed"}
    }
  }
  
  // Call DynamoDB to add the item to the table
  let result = await dynamo.send(new UpdateItemCommand(params)).catch((error: any) => {
    throw new Error(error);
  });

  console.log('confirmed flight reservation:');
  console.log(result);

  return {
    status: "ok",
    booking_id: reservationID
  }
};