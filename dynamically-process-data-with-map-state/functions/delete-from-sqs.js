const aws = require('aws-sdk');
const sqsQueueUrl = process.env.SQS_QUEUE_URL; 
exports.lambda_handler = (event, context, callback) => {
  const sqs = new aws.SQS();

  sqs.deleteMessage({
    QueueUrl: sqsQueueUrl,
    ReceiptHandle: event.ReceiptHandle
  }).promise()
    .then(data => {
      callback(null, data);
    })
    .catch(err => {
      callback(err);
    });
};