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
    try {
      const options = {
        hostname: url,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-HMAC-Signature": data.token,
          "Content-Length": payload.length,
        },
      };

      const req = https.request(options, (res) => {
        console.log(`statusCode: ${res.statusCode}`);

        res.on("data", (d) => {
          process.stdout.write(d);
        });
      });

      req.on("error", async (error) => {
        console.log("Task failed " + error);
        throw error;
      });

      req.write(payload);
      req.end();
      let params = {
        taskToken: data.taskToken,
        output: JSON.stringify({
          status: "success",
          output: {},
        }),
      };

      await client.send(new SendTaskSuccessCommand(params));
    } catch (error) {
      let params = {
        taskToken: data.taskToken,
        cause: "Webhook call failure",
        error: error.message,
      };

      await client.send(new SendTaskFailureCommand(params));
    }
  }
};
