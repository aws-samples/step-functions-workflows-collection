const { SNSClient, PublishCommand } = require("@aws-sdk/client-sns");
const { SSMClient, GetParameterCommand } = require("@aws-sdk/client-ssm");

const snsClient = new SNSClient();
const ssmClient = new SSMClient();

const input = { // GetParameterRequest
    Name: "CallBackEmailLambdaUrl"
 };

const getParameterCommand = new GetParameterCommand(input);
let lambdaUrl = "";

exports.handler = async function(event, context) {
    if (lambdaUrl == "") {
        const response = await ssmClient.send(getParameterCommand);
        lambdaUrl = response.Parameter.Value.replace(/\/$/, "");
    }

    const taskToken = event.taskToken;
    const quantity = event.quantityRequested + event.minPOAmount;
    
    const approveEndpoint = lambdaUrl + "?action=approve&taskToken=" + encodeURIComponent(taskToken);
    console.log('approveEndpoint= ' + approveEndpoint);

    const rejectEndpoint = lambdaUrl + "?action=reject&taskToken=" + encodeURIComponent(taskToken);
    console.log('rejectEndpoint= ' + rejectEndpoint);

    let emailMessage = 'This is an email requiring an approval for a purchase order for productId ' + event.productId + ' quantity ' + quantity + '. \n\n'
        emailMessage += 'Please click "Approve" link if you want to approve. \n\n'
        emailMessage += 'Approve ' + approveEndpoint + '\n\n'
        emailMessage += 'Reject ' + rejectEndpoint + '\n\n'
        emailMessage += 'Thanks for using Step functions!'

    const input = { // PublishInput
        TopicArn: process.env.SNS_TOPIC,
        Message: emailMessage,
        Subject: "Purchase Order request"
      };
      const command = new PublishCommand(input);
      const response = await snsClient.send(command);
      return response;   
}