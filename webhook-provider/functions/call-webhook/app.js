const https = require("https");

const {
  SFNClient,
  SendTaskFailureCommand,
  SendTaskSuccessCommand,
} = require("@aws-sdk/client-sfn");

const client = new SFNClient({ region: process.env.REGION });

/*
 * Makes an HTTPS POST request to the specified URL with the given payload and options.
 * @param {string} url - The URL to make the POST request to.
 * @param {string} payload - The payload data to send in the request body.
 * @param {object} options - The options object for configuring the request.
 * @returns {Promise<object>} - A promise that resolves with the parsed response data.
 */
let callWebhook = async (url, payload, options) =>
  new Promise((resolve, reject) => {
    const req = https.request(url, options, (res) => {
      let buffer = "";
      res.on("data", (chunk) => (buffer += chunk));

      res.on("end", () => resolve(JSON.parse(buffer)));
    });

    req.on("error", (e) => {
      console.log(e);
      reject(e.message);
    });
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Request timeout"));
    });
    req.write(payload);
    req.end();
  });

/**
 * Lambda function for processing events from an SQS queue and making HTTPS requests.
 * Handles success and failure notifications through AWS Step Functions.
 
 */
module.exports.lambdaHandler = async (event) => {
  for (const message of event.Records) {
    var data = JSON.parse(message.body);

    data.payload.notificationTime = Date.now();
    var payload = JSON.stringify(data.payload);
    let url = data.url;

    const options = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-HMAC-Signature": data.token,
        "Content-Length": payload.length,
      },
      timeout: 5000,
    };

    let response = await callWebhook(url, payload, options)
      .then(async (result) => {
        let params = {
          taskToken: data.taskToken,
          output: JSON.stringify({
            status: "success",
            output: result,
          }),
        };

        await client.send(new SendTaskSuccessCommand(params));
      })
      .catch(async (error) => {
        let params = {
          taskToken: data.taskToken,
          cause: "Webhook call failure",
          error: error.message,
        };

        await client.send(new SendTaskFailureCommand(params));
      });
  }
};
