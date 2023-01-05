const { DynamoDBClient, ImportTableCommand } = require("@aws-sdk/client-dynamodb");
const client = new DynamoDBClient();

const { S3_BUCKET } = process.env;

const startImportTable = async (prefix, TableParams) => {
  const params = {
    InputFormat: "DYNAMODB_JSON", 
    S3BucketSource: {
      S3Bucket: S3_BUCKET,
      S3KeyPrefix: prefix
    },
    TableCreationParameters: TableParams
  }
  console.log('PARAMS:', params)
  const command = new ImportTableCommand(params)
  return await client.send(command);
}

exports.handler = async (event) => {
  console.log('EVENT:', event)
  try {
    // Remove Null Values
    const cleanArray = event.filter(x => x)
    // Filter to Find S3 Bucket Prefix
    const prefix = ( cleanArray.filter(i => i.includes('.json')) )[0].split('/')[0]
    console.log('PREFIX:', prefix)
    // Filter to Find TableCreationParams from start-workflow json file
    const tableCreateParams = ( cleanArray.filter(i => i.includes('TableName')) )[0]
    console.log('TABLE PARAMS:', tableCreateParams)

    return await startImportTable(prefix, JSON.parse(tableCreateParams))
  }
  catch (err) {
    console.error(err)
    throw err
  }
}