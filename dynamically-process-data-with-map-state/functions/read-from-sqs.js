const { SQSClient, ReceiveMessageCommand } = require('@aws-sdk/client-sqs');
const sqsQueueUrl = process.env.SQS_QUEUE_URL; 
const sqs = new SQSClient();

exports.lambda_handler = async (event) => {
  const data = await sqs.send(new ReceiveMessageCommand({
    QueueUrl: sqsQueueUrl,
    MessageSystemAttributeNames: ['All'],
    MaxNumberOfMessages: 10,
    VisibilityTimeout: 30,
    WaitTimeSeconds: 20
  }));
  if (!data.Messages) {
    return "No messages";
  }
  return data.Messages;
};
