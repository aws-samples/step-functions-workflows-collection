const aws = require('aws-sdk');
const s3 = new aws.S3({ apiVersion: '2006-03-01' });
const db = new aws.DynamoDB.DocumentClient();
const stepfunctions = new aws.StepFunctions();
const dbTableName = process.env.DB_TABLE_NAME;

exports.handler = async (event, context) => {

    // console.log(JSON.stringify(event, null, 2));
    
    var waitLater = false;
    
    try {
        console.log("requesting object restore");

        var data = await s3.restoreObject({
            Bucket: event.bucket,
            Key: event.key,
            RestoreRequest: {
                Days: 1, 
                GlacierJobParameters: {
                    Tier: "Standard"
                }
            }
        }).promise();
        waitLater = true;
        
    } catch (err) {
        if(err.code == 'RestoreAlreadyInProgress') {
            console.log("restore already in progress");
            //then just add the task token to dynamodb and proceed
            waitLater = true;
        } else {
            console.error(err);
            const params = {
                taskToken: event.taskToken,
                cause: "Failed to restore object",
                error: err.code
            };
            await stepfunctions.sendTaskFailure(params).promise();
            console.log("task errored");
        }
        
    }
    
    if(waitLater) {
    
        console.log("adding task token to dynamodb");
    
        var res = await db.update({
            TableName: dbTableName,
            Key: { S3Bucket: event.bucket, S3Key: event.key },
            ReturnValues: 'ALL_NEW',
            UpdateExpression: 'set #taskTokens = list_append(if_not_exists(#taskTokens, :empty_list), :token)',
            ExpressionAttributeNames: {
              '#taskTokens': 'taskTokens'
            },
            ExpressionAttributeValues: {
              ':token': [event.taskToken],
              ':empty_list': []
            }
          }).promise()
          
        // console.log(res);
        
    }
    
};
