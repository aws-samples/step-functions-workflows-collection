import {
  DynamoDBClient,
  GetItemCommandInput,
  UpdateItemCommandInput,
} from '@aws-sdk/client-dynamodb';
import {
  SFNClient,
  SendTaskSuccessCommand,
  SendTaskSuccessCommandInput,
} from '@aws-sdk/client-sfn';
import {
  DynamoDBDocumentClient,
  PutCommand,
  GetCommand,
  PutCommandInput,
  QueryCommand,
  QueryCommandInput,
  QueryCommandOutput,
  UpdateCommand,
} from '@aws-sdk/lib-dynamodb';

const sfnClient = new SFNClient({ region: process.env.AWS_REGION });
const DDB_TABLE = process.env.DDB_TABLE;
const ddbClient = new DynamoDBClient({ region: process.env.AWS_REGION });
const ddbDocClient = DynamoDBDocumentClient.from(ddbClient);

export const handler = async (
  event: any,
  context: any,
  callback: (arg0: null) => void,
) => {
  console.log(event);

  const versionId = event.detail['version-id'];

  const taskToken = await getItem({
    TableName: DDB_TABLE,
    Key: {
      PK1: versionId,
    },
  });
  const response = await executeSfnCallBack(taskToken.Item.TT);
  console.log(response);
  await updateItem({
    TableName: DDB_TABLE,
    Key: {
      PK1: versionId,
    },
    ProjectionExpression: '#st',
    ExpressionAttributeNames: { '#st': 'STATUS' },
    UpdateExpression: 'set expiry = :tt, #st = :st',
    ExpressionAttributeValues: {
      ':st': 'PROCESSED',
      ':tt': Math.floor(Date.now() / 1000) + 7 * 24 * 60 * 60,
    },
  });
};

async function executeSfnCallBack(taskToken: string) {
  const input: SendTaskSuccessCommandInput = {
    taskToken: taskToken,
    output: JSON.stringify({
      finishedTime: new Date().toISOString(),
      status: 'SUCCESS',
    }),
  };

  const command = new SendTaskSuccessCommand(input);

  try {
    await sfnClient.send(command);
  } catch (error) {
    console.log(`Error: ${error}`);
  }
  return { response: 200, message: 'Callback Executed Succesfully' };
}

async function getItem(queryInput: GetItemCommandInput) {
  try {
    const data = await ddbDocClient.send(new GetCommand(queryInput));
    console.log('Success :', data.Item);
    return data;
  } catch (err) {
    console.log('Error', err);
  }
}

async function updateItem(updateInput: UpdateItemCommandInput) {
  try {
    const data = await ddbDocClient.send(new UpdateCommand(updateInput));
    console.log('Success :', data.Item);
    return data;
  } catch (err) {
    console.log('Error', err);
  }
}

async function query(
  queryInput: QueryCommandInput,
): Promise<QueryCommandOutput> {
  try {
    return await ddbDocClient.send(new QueryCommand(queryInput));
  } catch (err) {
    console.log(err);
    handleGetItemError(err);
    return err;
  }
}
export async function execute(queryInput: QueryCommandInput | PutCommandInput) {
  const data = await query(queryInput);
  return data;
}

function handleGetItemError(err: any) {
  if (!err) {
    console.error('Encountered error object was empty');
    return;
  }
  if (!err.code) {
    console.error(
      `An exception occurred, investigate and configure retry strategy. Error: ${JSON.stringify(
        err,
      )}`,
    );
    return;
  }
  // here are no API specific errors to handle for GetItem, common DynamoDB API errors are handled below
  handleCommonErrors(err);
}

function handleCommonErrors(err: any) {
  switch (err.code) {
    case 'InternalServerError':
      console.error(
        `Internal Server Error, generally safe to retry with exponential back-off. Error: ${err.message}`,
      );
      return;
    case 'ProvisionedThroughputExceededException':
      console.error(
        `Request rate is too high. If you're using a custom retry strategy make sure to retry with exponential back-off.` +
          `Otherwise consider reducing frequency of requests or increasing provisioned capacity for your table or secondary index. Error: ${err.message}`,
      );
      return;
    case 'ResourceNotFoundException':
      console.error(
        `One of the tables was not found, verify table exists before retrying. Error: ${err.message}`,
      );
      return;
    case 'ServiceUnavailable':
      console.error(
        `Had trouble reaching DynamoDB. generally safe to retry with exponential back-off. Error: ${err.message}`,
      );
      return;
    case 'ThrottlingException':
      console.error(
        `Request denied due to throttling, generally safe to retry with exponential back-off. Error: ${err.message}`,
      );
      return;
    case 'UnrecognizedClientException':
      console.error(
        `The request signature is incorrect most likely due to an invalid AWS access key ID or secret key, fix before retrying.` +
          `Error: ${err.message}`,
      );
      return;
    case 'ValidationException':
      console.error(
        `The input fails to satisfy the constraints specified by DynamoDB, ` +
          `fix input before retrying. Error: ${err.message}`,
      );
      return;
    case 'RequestLimitExceeded':
      console.error(
        `Throughput exceeds the current throughput limit for your account, ` +
          `increase account level throughput before retrying. Error: ${err.message}`,
      );
      return;
    default:
      console.error(
        `An exception occurred, investigate and configure retry strategy. Error: ${err.message}`,
      );
      return;
  }
}
