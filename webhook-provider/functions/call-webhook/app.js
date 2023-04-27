const https = require("https");

module.exports.lambdaHandler = async (event) => {
  for (const message of event.Records) {
 
  const data = JSON.stringify({
   'resource': message.resourceType,
   'Event' : message.eventType,
   'resourceId': message.resourceId,
  });

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
      message: 'processed records',
      input: event,
    },
    null,
    2
  ),
};

};

let callapi = async (url, payload, options) =>
  new Promise((resolve, reject) => {
    let buffer = "";

    const req = https.request(url, options, (res) => {
      let buffer = "";
      res.on("data", (chunk) => (buffer += chunk));

      res.on("end", () => resolve(JSON.parse(buffer)));
    });

    req.on("error", (e) => reject(e.message));
    req.write(payload);
    req.end();
  });
