exports.lambdaHandler = async(event: { Records: any; }, context: any, callback: any) => {
    
    await new Promise(resolve => setTimeout(resolve, 300));
      return { "statusCode": 200,
      "body": {
        "updated": true
      }
    }
}