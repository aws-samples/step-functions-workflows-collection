const axios = require('axios')
const http = require('http');

exports.lambdaHandler = async (event, context) => {
  console.debug(event)
  if (event.enableLog) {
    console.log("Making request with config: ", event.config)
  }
  
  if (!event.config) {
    throw Error("Missing HTTP request config in the input.")
  }
  
  let config = event.config
  if (!(event in forceIPv4) or event.forceIPv4){
    // Lambda functions don't support outbound IPv6 yet, force IPv4
    console.debug("Forcing axios to use IPv4")
    const agent = new http.Agent({ family: 4 });
    config = {...config, httpAgent: agent}
  }
  const resp = await axios(config)
  .catch(function (error) {
    console.error(error)
    throw error
  });
  
  if (event.enableLog) {
    console.log(`Received response status ${resp.status}`)
  }
  
  return {
       status: resp.status,
       headers: resp.headers,
       response: resp.data
    }
}
