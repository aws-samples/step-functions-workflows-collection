const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, UpdateCommand } = require("@aws-sdk/lib-dynamodb");
const DDB = DynamoDBDocumentClient.from(new DynamoDBClient({}));

const { TABLE_NAME } = process.env;

const updateDDB = async ({id, taskToken}) => {
    // Update record with task token
    const params = {
        TableName: TABLE_NAME,
        Key: {id: id},
        UpdateExpression: 'set taskToken = :tk',
        ExpressionAttributeValues: {
            ':tk' : taskToken
          }
    }
    console.log('PARAMS:', params)
    const res = await DDB.send(new UpdateCommand(params))
    console.log('DDB RES:', res)
    return res;
}

exports.handler = async (event) => {
    try {
        const {Sns} = event.Records[0]
        console.log('EVENT:', Sns);
        // Parse Params from body
        const {id, taskToken} = JSON.parse(Sns.Message)

        // Send Task Token
        const res = await updateDDB({id, taskToken})
        return res
        
    }
    catch (err) {
        console.error(err)
    }

};