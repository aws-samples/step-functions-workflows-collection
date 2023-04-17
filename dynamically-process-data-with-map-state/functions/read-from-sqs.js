const aws = require('aws-sdk');
const sqsQueueUrl = process.env.SQS_QUEUE_URL; 
exports.lambda_handler = (event, context, callback) => {
  const sqs = new aws.SQS();

  sqs.receiveMessage({
    QueueUrl: sqsQueueUrl,
    AttributeNames: ['All'],
    MaxNumberOfMessages: '10',
    VisibilityTimeout: '30',
    WaitTimeSeconds: '20'
  }).promise()
    .then(data => {
      if (!data.Messages) {
        callback(null, "No messages");
      } else {
        callback(null, data.Messages);
      }
    })
    .catch(err => {
      callback(err);
    });
};