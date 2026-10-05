const { SQSClient, DeleteMessageCommand } = require('@aws-sdk/client-sqs');
const sqsQueueUrl = process.env.SQS_QUEUE_URL; 
const sqs = new SQSClient();

exports.lambda_handler = async (event) => {
  return await sqs.send(new DeleteMessageCommand({
    QueueUrl: sqsQueueUrl,
    ReceiptHandle: event.ReceiptHandle
  }));
};
