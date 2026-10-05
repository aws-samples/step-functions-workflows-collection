const { S3Client, RestoreObjectCommand } = require('@aws-sdk/client-s3');
const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, UpdateCommand } = require('@aws-sdk/lib-dynamodb');
const { SFNClient, SendTaskFailureCommand } = require('@aws-sdk/client-sfn');
const s3 = new S3Client({});
const db = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const stepfunctions = new SFNClient({});
const dbTableName = process.env.DB_TABLE_NAME;

exports.handler = async (event, context) => {

    // console.log(JSON.stringify(event, null, 2));
    
    var waitLater = false;
    
    try {
        console.log("requesting object restore");

        var data = await s3.send(new RestoreObjectCommand({
            Bucket: event.bucket,
            Key: event.key,
            RestoreRequest: {
                Days: 1, 
                GlacierJobParameters: {
                    Tier: "Standard"
                }
            }
        }));
        waitLater = true;
        
    } catch (err) {
        if(err.name == 'RestoreAlreadyInProgress') {
            console.log("restore already in progress");
            //then just add the task token to dynamodb and proceed
            waitLater = true;
        } else {
            console.error(err);
            const params = {
                taskToken: event.taskToken,
                cause: "Failed to restore object",
                error: err.name
            };
            await stepfunctions.send(new SendTaskFailureCommand(params));
            console.log("task errored");
        }
        
    }
    
    if(waitLater) {
    
        console.log("adding task token to dynamodb");
    
        var res = await db.send(new UpdateCommand({
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
          }))
          
        // console.log(res);
        
    }
    
};
