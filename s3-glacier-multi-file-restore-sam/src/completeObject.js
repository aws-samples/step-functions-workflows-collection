const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, GetCommand, DeleteCommand } = require('@aws-sdk/lib-dynamodb');
const { SFNClient, SendTaskSuccessCommand } = require('@aws-sdk/client-sfn');
const db = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const stepfunctions = new SFNClient({});
const dbTableName = process.env.DB_TABLE_NAME;

exports.handler = async (event, context) => {
    
    // console.log(JSON.stringify(event, null, 2));    
    
    const bucket = event.detail.bucket.name;
    const key = event.detail.object.key;

    console.log("restore complete for " + key);
    
    var params = {
        TableName: dbTableName,
        Key: {
            S3Bucket: bucket,
            S3Key: key
        }
    };
    var data = await db.send(new GetCommand(params));
    
    if(!data.Item) {
        console.error("failed to get task token for " + key);
        return;
    }
    
    var taskTokens = data.Item.taskTokens;
    
    //remove any duplicates
    var filteredTokens = taskTokens.filter(function(item, pos){
      return taskTokens.indexOf(item)== pos; 
    });
    
    for(const token of taskTokens) {
        try {
            const params = {
                taskToken: token,
                output: JSON.stringify({
                  "bucket": bucket,
                  "key": key
                })
            };
            await stepfunctions.send(new SendTaskSuccessCommand(params));
        } catch (err) {
            console.error(err);
        }
    }
    
    await db.send(new DeleteCommand(params));
    
};
