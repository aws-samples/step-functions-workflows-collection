// const axios = require('axios')
// const url = 'http://checkip.amazonaws.com/';
const axios = require('axios')
let response;
const endpoont = process.env.endPoint
exports.lambdaHandler = async (event, context) => {

    const nextItem= event.assignee
    const config = {
        method: 'post',
        url: endpoont,
                headers: { 
                'Content-Type': 'application/json', 
                'Cookie': 'TooBusyRedirectCount=0'
                },
        data : {nextItem:nextItem}
        }
          
  
  const t= await axios(config)
  .then(function (response) {
    console.log(JSON.stringify(response.data));
  })
  .catch(function (error) {
    console.log(error);
  });
  
   return {
       statusCode: 200, 
       body: JSON.stringify({ message: t })
    }
  }