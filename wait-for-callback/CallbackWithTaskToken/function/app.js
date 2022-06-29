 /**
              MIT No Attribution
              
              Copyright 2022 Amazon Web Services
              
              Permission is hereby granted, free of charge, to any person obtaining a copy of this
              software and associated documentation files (the "Software"), to deal in the Software
              without restriction, including without limitation the rights to use, copy, modify,
              merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
              permit persons to whom the Software is furnished to do so.
              
              THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
              INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
              PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
              HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
              OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
              SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
          */

              console.log('Loading function');

              var AWS = require('aws-sdk');
              var stepfunctions = new AWS.StepFunctions({apiVersion: '2016-11-23'});
    
              exports.lambdaHandler = async(event, context, callback) => {
    
                  for (const record of event.Records) {
                      const messageBody = JSON.parse(record.body);
                      const taskToken = messageBody.TaskToken;
    
                      const params = {
                          output: "\"Callback task completed successfully.\"",
                          taskToken: taskToken
                      };
    
                       console.log(`Calling Step Functions to complete callback task with params ${JSON.stringify(params)}`);
                       let response = await stepfunctions.sendTaskSuccess(params).promise();
                  }
              };