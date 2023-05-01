const https = require("https");

const {
  SFNClient,
  SendTaskFailureCommand,
  SendTaskSuccessCommand,
} = require("@aws-sdk/client-sfn");
const { resolve } = require("path");

const client = new SFNClient({ region: process.env.REGION });

module.exports.lambdaHandler = async (event) => {
  for (const message of event.Records) {
    var data = JSON.parse(message.body);
    console.log(data);
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
      timeout: 5000 
    };

    console.log(options);
    let response = await callapi(url, payload, options)
      .then(async (result) => {
        let params = {
          taskToken: data.taskToken,
          output: JSON.stringify({
            status: "success",
            output: result,
          }),
        };
        console.log(params);
        await client.send(new SendTaskSuccessCommand(params));
      })
      .catch(async (error) => {
        let params = {
          taskToken: data.taskToken,
          cause: "Webhook call failure",
          error: error,
        };
        console.log(params);
        await client.send(new SendTaskFailureCommand(params));
      });
  }
};

let callapi = async (url, payload, options) =>
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
      reject("timeout");

    });
    req.write(payload);
    req.end();
  });
