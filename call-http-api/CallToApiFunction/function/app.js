const axios = require('axios')

exports.lambdaHandler = async (event, context) => {
  console.debug(event)
  if (event.enableLog) {
    console.log("Making request with config: ", event.config)
  }
  
  if (!event.config) {
    throw Error("Missing HTTP request config in the input.")
  }
  
  const resp = await axios(event.config)
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