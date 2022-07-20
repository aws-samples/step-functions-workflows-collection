import {
  SFNClient,
  SendTaskSuccessCommand,
  SendTaskSuccessCommandInput,
} from '@aws-sdk/client-sfn';
import {
  DeleteMessageCommand,
  ReceiveMessageCommand,
  SQSClient,
} from '@aws-sdk/client-sqs';

const sfnClient = new SFNClient({ region: process.env.AWS_REGION });
const sqsClient = new SQSClient({ region: process.env.AWS_REGION });
const SQS_QUEUE_URL = process.env.SQS_QUEUE_URL;

export const handler = async (
  event: { Records: any },
  context: any,
  callback: (arg0: null) => void,
) => {
  for (const record of event.Records) {
    const message = JSON.parse(record['Sns']['Message']);
    const jobId = message['JobId'];

    const taskTokens = await getSqsTaskToken(jobId);

    const response = await executeSfnCallBack(taskTokens);
    console.log(response);
  }
};

async function executeSfnCallBack(taskTokens: string[]) {
  await Promise.all(
    taskTokens.map(async (taskToken) => {
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
    }),
  );

  return { response: 200, message: 'Callback Executed Succesfully' };
}

async function getSqsTaskToken(sqsGroupId: any) {
  const params = {
    QueueUrl: SQS_QUEUE_URL,
    WaitTimeSeconds: 15,
    MessageGroupId: sqsGroupId,
  };
  const command = new ReceiveMessageCommand(params);
  const { Messages } = await sqsClient.send(command);

  const taskTokens: string[] = [];

  if (Messages?.length) {
    await Promise.all(
      Messages.map(async (message) => {
        if (message.Body?.length) {
          const sqsMessage = JSON.parse(message.Body);
          taskTokens.push(sqsMessage['TaskToken']);
        }

        const command = new DeleteMessageCommand({
          QueueUrl: SQS_QUEUE_URL,
          ReceiptHandle: message.ReceiptHandle,
        });
        await sqsClient.send(command);
      }),
    );
  }

  return taskTokens;
}
