const AWS = require('aws-sdk');
const s3 = new AWS.S3();
const { marshall } = require("@aws-sdk/util-dynamodb");

const { S3_BUCKET } = process.env

// get file from S3
const getS3File = async (Key) => {
    const params = {
        Bucket: S3_BUCKET,
        Key: Key
    };
    return await s3.getObject(params).promise();
}

// Marshall JSON to DDB JSON
const marshallJson = async (file) => {
  let DDBjson = ''
  JSON.parse(file).forEach(item => {
    const obj = { Item: marshall(item) }
    DDBjson += JSON.stringify(obj) + '\n'
  })
  return DDBjson;
}

// Save file to S3 bucket
const saveFileToS3 = async (Key, file) => {
  // Create New Key
  const NewKey = `${Key.split('/')[0]}-CONVERTED/${Key.split('/')[1]}`
  const params = {
    Bucket: S3_BUCKET,
    Key: NewKey,
    Body: file
  }
  await s3.upload(params).promise()
  return NewKey
}

exports.handler = async (event) => {
  console.log('EVENT:', event)
  const {Key} = event
  try {
    // Skip over folder iterator E.g. something-here/
    if (Key.split('.')[1] != 'json') return

    // Get JSON file from S3
    const jsonFile = await getS3File(Key)
    // If start-sorkflow file then return contents
    if (Key.split('/')[1] === 'start-workflow.json') return jsonFile.Body.toString()
    // Marshall JSON file
    const marshalledJson = await marshallJson(jsonFile.Body.toString('utf-8'))
    // Save file to S3 bucket
    const saveFile = await saveFileToS3(Key, marshalledJson)

    return saveFile;
  }
  catch (err) {
    console.error(err)
    return err
  }
}