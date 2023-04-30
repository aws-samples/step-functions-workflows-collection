const https = require("https");

module.exports.lambdaHandler = async (event) => {
  for (const message of event.Records) {
    const data = JSON.stringify({
      resource: message.resourceType,
      Event: message.eventType,
      resourceId: message.resourceId,
      createdAt: message.createdAt,
    });

    //TODO: Decrypt and add the authz
    let url = message.callbackURL;
    const options = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": data.length,
      },
    };

    let response = callapi(url, data, options);
    console.log("Sent notification to customer");
  }
  return {
    statusCode: 200,
    body: JSON.stringify(
      {
        message: "processed records",
        input: event,
      },
      null,
      2
    ),
  };
};


async function callapi(url, payload, options) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      console.log(`statusCode: ${res.statusCode}`);

      res.on("data", (d) => {
        process.stdout.write(payload);
      });
    });

    req.on("error", (error) => {
      reject(req);
      console.error(error);
    });

    // set a timeout of 5 seconds
    req.setTimeout(5000, () => {
      req.destroy();
    });

    req.end();
    resolve(req);
  });
}
