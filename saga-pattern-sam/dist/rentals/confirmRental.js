"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.handler = void 0;
const { DynamoDB } = require('aws-sdk');
exports.handler = async function (event) {
    console.log("request:", JSON.stringify(event, undefined, 2));
    // Pass the parameter to fail this step 
    if (event.run_type === 'failCarRentalConfirmation') {
        throw new Error('Failed to book the car rental');
    }
    let reservationID = '';
    if (typeof event.ReserveCarRentalResult !== 'undefined') {
        reservationID = event.ReserveCarRentalResult.Payload.booking_id;
    }
    const dynamo = new DynamoDB();
    var params = {
        TableName: process.env.TABLE_NAME,
        Key: {
            'pk': { S: event.trip_id },
            'sk': { S: 'CAR#' + reservationID }
        },
        "UpdateExpression": "set transaction_status = :booked",
        "ExpressionAttributeValues": {
            ":booked": { "S": "confirmed" }
        }
    };
    // Call DynamoDB to add the item to the table
    let result = await dynamo.updateItem(params).promise().catch((error) => {
        throw new Error(error);
    });
    console.log('confirmed car rental reservation:');
    console.log(result);
    return {
        status: "ok",
        booking_id: reservationID
    };
};
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiY29uZmlybVJlbnRhbC5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbIi4uLy4uL2xhbWJkYXMvcmVudGFscy9jb25maXJtUmVudGFsLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7OztBQUFBLE1BQU0sRUFBRSxRQUFRLEVBQUUsR0FBRyxPQUFPLENBQUMsU0FBUyxDQUFDLENBQUM7QUFHM0IsUUFBQSxPQUFPLEdBQUcsS0FBSyxXQUFVLEtBQVM7SUFDN0MsT0FBTyxDQUFDLEdBQUcsQ0FBQyxVQUFVLEVBQUUsSUFBSSxDQUFDLFNBQVMsQ0FBQyxLQUFLLEVBQUUsU0FBUyxFQUFFLENBQUMsQ0FBQyxDQUFDLENBQUM7SUFFN0Qsd0NBQXdDO0lBQ3hDLElBQUcsS0FBSyxDQUFDLFFBQVEsS0FBSywyQkFBMkIsRUFBQztRQUM5QyxNQUFNLElBQUksS0FBSyxDQUFDLCtCQUErQixDQUFDLENBQUM7S0FDcEQ7SUFFRCxJQUFJLGFBQWEsR0FBRyxFQUFFLENBQUM7SUFDdkIsSUFBSSxPQUFPLEtBQUssQ0FBQyxzQkFBc0IsS0FBSyxXQUFXLEVBQUU7UUFDdkQsYUFBYSxHQUFHLEtBQUssQ0FBQyxzQkFBc0IsQ0FBQyxPQUFPLENBQUMsVUFBVSxDQUFDO0tBQ2pFO0lBR0QsTUFBTSxNQUFNLEdBQUcsSUFBSSxRQUFRLEVBQUUsQ0FBQztJQUU5QixJQUFJLE1BQU0sR0FBSTtRQUNaLFNBQVMsRUFBRSxPQUFPLENBQUMsR0FBRyxDQUFDLFVBQVU7UUFDakMsR0FBRyxFQUFFO1lBQ0gsSUFBSSxFQUFHLEVBQUMsQ0FBQyxFQUFFLEtBQUssQ0FBQyxPQUFPLEVBQUM7WUFDekIsSUFBSSxFQUFHLEVBQUMsQ0FBQyxFQUFFLE1BQU0sR0FBQyxhQUFhLEVBQUM7U0FDakM7UUFDRCxrQkFBa0IsRUFBRSxrQ0FBa0M7UUFDdEQsMkJBQTJCLEVBQUU7WUFDekIsU0FBUyxFQUFFLEVBQUMsR0FBRyxFQUFFLFdBQVcsRUFBQztTQUNoQztLQUNGLENBQUE7SUFFRCw2Q0FBNkM7SUFDN0MsSUFBSSxNQUFNLEdBQUcsTUFBTSxNQUFNLENBQUMsVUFBVSxDQUFDLE1BQU0sQ0FBQyxDQUFDLE9BQU8sRUFBRSxDQUFDLEtBQUssQ0FBQyxDQUFDLEtBQVUsRUFBRSxFQUFFO1FBQzFFLE1BQU0sSUFBSSxLQUFLLENBQUMsS0FBSyxDQUFDLENBQUM7SUFDekIsQ0FBQyxDQUFDLENBQUM7SUFFSCxPQUFPLENBQUMsR0FBRyxDQUFDLG1DQUFtQyxDQUFDLENBQUM7SUFDakQsT0FBTyxDQUFDLEdBQUcsQ0FBQyxNQUFNLENBQUMsQ0FBQztJQUVwQixPQUFPO1FBQ0wsTUFBTSxFQUFFLElBQUk7UUFDWixVQUFVLEVBQUUsYUFBYTtLQUMxQixDQUFBO0FBQ0gsQ0FBQyxDQUFDIiwic291cmNlc0NvbnRlbnQiOlsiY29uc3QgeyBEeW5hbW9EQiB9ID0gcmVxdWlyZSgnYXdzLXNkaycpO1xuZXhwb3J0IHt9O1xuXG5leHBvcnQgY29uc3QgaGFuZGxlciA9IGFzeW5jIGZ1bmN0aW9uKGV2ZW50OmFueSkge1xuICBjb25zb2xlLmxvZyhcInJlcXVlc3Q6XCIsIEpTT04uc3RyaW5naWZ5KGV2ZW50LCB1bmRlZmluZWQsIDIpKTtcblxuICAvLyBQYXNzIHRoZSBwYXJhbWV0ZXIgdG8gZmFpbCB0aGlzIHN0ZXAgXG4gIGlmKGV2ZW50LnJ1bl90eXBlID09PSAnZmFpbENhclJlbnRhbENvbmZpcm1hdGlvbicpe1xuICAgICAgdGhyb3cgbmV3IEVycm9yKCdGYWlsZWQgdG8gYm9vayB0aGUgY2FyIHJlbnRhbCcpO1xuICB9XG5cbiAgbGV0IHJlc2VydmF0aW9uSUQgPSAnJztcbiAgaWYgKHR5cGVvZiBldmVudC5SZXNlcnZlQ2FyUmVudGFsUmVzdWx0ICE9PSAndW5kZWZpbmVkJykge1xuICAgIHJlc2VydmF0aW9uSUQgPSBldmVudC5SZXNlcnZlQ2FyUmVudGFsUmVzdWx0LlBheWxvYWQuYm9va2luZ19pZDtcbiAgfVxuXG5cbiAgY29uc3QgZHluYW1vID0gbmV3IER5bmFtb0RCKCk7XG5cbiAgdmFyIHBhcmFtcyAgPSB7XG4gICAgVGFibGVOYW1lOiBwcm9jZXNzLmVudi5UQUJMRV9OQU1FLFxuICAgIEtleToge1xuICAgICAgJ3BrJyA6IHtTOiBldmVudC50cmlwX2lkfSxcbiAgICAgICdzaycgOiB7UzogJ0NBUiMnK3Jlc2VydmF0aW9uSUR9XG4gICAgfSxcbiAgICBcIlVwZGF0ZUV4cHJlc3Npb25cIjogXCJzZXQgdHJhbnNhY3Rpb25fc3RhdHVzID0gOmJvb2tlZFwiLFxuICAgIFwiRXhwcmVzc2lvbkF0dHJpYnV0ZVZhbHVlc1wiOiB7XG4gICAgICAgIFwiOmJvb2tlZFwiOiB7XCJTXCI6IFwiY29uZmlybWVkXCJ9XG4gICAgfVxuICB9XG4gIFxuICAvLyBDYWxsIER5bmFtb0RCIHRvIGFkZCB0aGUgaXRlbSB0byB0aGUgdGFibGVcbiAgbGV0IHJlc3VsdCA9IGF3YWl0IGR5bmFtby51cGRhdGVJdGVtKHBhcmFtcykucHJvbWlzZSgpLmNhdGNoKChlcnJvcjogYW55KSA9PiB7XG4gICAgdGhyb3cgbmV3IEVycm9yKGVycm9yKTtcbiAgfSk7XG5cbiAgY29uc29sZS5sb2coJ2NvbmZpcm1lZCBjYXIgcmVudGFsIHJlc2VydmF0aW9uOicpO1xuICBjb25zb2xlLmxvZyhyZXN1bHQpO1xuXG4gIHJldHVybiB7XG4gICAgc3RhdHVzOiBcIm9rXCIsXG4gICAgYm9va2luZ19pZDogcmVzZXJ2YXRpb25JRFxuICB9XG59OyJdfQ==