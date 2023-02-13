const AWS = require('aws-sdk');


const stepFunctions = new AWS.StepFunctions({
});

module.exports.handler = (event:any, context:any, callback:any) => {
    
    let runType = "success"; // failFlightsReservation , failFlightsConfirmation , failCarRentalReservation, failCarRentalConfirmation, failPayment
    let tripID =  context.awsRequestId;
    
    if(null != event.queryStringParameters){
        if(typeof event.queryStringParameters.runType != 'undefined') {
            runType = event.queryStringParameters.runType;
        }

        if(typeof event.queryStringParameters.tripID != 'undefined') {
            tripID = event.queryStringParameters.tripID;
        }
    }

    let input = {
        "trip_id": tripID,
        "depart_city": "Detroit",
        "depart_time": "2021-07-07T06:00:00.000Z",
        "arrive_city": "Frankfurt",
        "arrive_time": "2021-07-09T08:00:00.000Z",
        "rental": "BMW",
        "rental_from": "2021-07-09T00:00:00.000Z",
        "rental_to": "2021-07-17T00:00:00.000Z",
        "run_type": runType
    };
    
    const params = {
        stateMachineArn: process.env.statemachine_arn,
        input: JSON.stringify(input)
    };
    
    stepFunctions.startExecution(params, (err:any, data:any) => {
        if (err) {
        
            console.log(err);
            const response = {
                statusCode: 500,
                body: JSON.stringify({
                message: 'There was an error processing your reservation'
                })
            };
            callback(null, response);
        } else {
            
            console.log(data);
            const response = {
                statusCode: 200,
                body: JSON.stringify({
                    message: 'Your reservation is being processed'
                })
            };
            callback(null, response);
        }
    });
};