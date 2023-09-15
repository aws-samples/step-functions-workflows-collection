const { CloudFormationClient, DescribeStacksCommand } = require('@aws-sdk/client-cloudformation');
const { HttpRequest } = require('@aws-sdk/protocol-http')
const { defaultProvider } = require('@aws-sdk/credential-provider-node')
const { SignatureV4 } = require('@aws-sdk/signature-v4')
const { Sha256 } = require('@aws-crypto/sha256-browser')

const stackName = process.env.AWS_SAM_STACK_NAME;
const region = process.env.AWS_REGION;
const cfClient = new CloudFormationClient({ region: region });

async function getApiEndpoint() {

    if (!stackName) {
        throw new Error('Cannot find env var AWS_SAM_STACK_NAME. Please include the stack name when running integration tests.')
    }
    
    const input = {
        StackName: stackName,
    };    
    const stackObj = await cfClient.send(new DescribeStacksCommand(input));
    if (!stackObj){
        throw new Error('Missing required resources');
    }
    const endpoint = stackObj.Stacks[0].Outputs.find((item) => item.OutputKey === 'RestApiEndpoint').OutputValue;
    
    if (!endpoint) {
        throw new Error('Missing required CloudFormation resources');
    }    
    return endpoint
};

async function streamToString(stream) {
    const chunks = [];
    
    for await (const chunk of stream) {        
        try {
            const buf = Buffer.from(chunk);
            // both results can be streamed in the same buffer            
            const sbuf = buf.toString("utf-8").split('\n').slice(0, -1);                                    
            for (const jsonLine of sbuf){
                const j = JSON.parse(jsonLine);
                console.log('streamed json:', j);                
            }
            chunks.push(buf);    
        } catch (error) {
            console.log('error:', error);            
        }
    }

    return Buffer.concat(chunks).toString("utf-8");
}

(async () => {
    
    const apiGatewayUrl = await getApiEndpoint();
    const response = await fetch(apiGatewayUrl, {
        method: 'POST'         
    }).catch((err) => {
        console.log(err)
        throw new Error(err);
    });

    const jsonResponse = await response.json();    
    const resultStreamingLambdaUrl = jsonResponse.workflow.completeLambdaResultURL;
    console.log("StreamingResultsLambdaUrl:", resultStreamingLambdaUrl)
    const signer = new SignatureV4({
        credentials: defaultProvider(),
        region: region,
        service: 'lambda',
        sha256: Sha256
    })

    const streamUrl = new URL(resultStreamingLambdaUrl)
    var params = {}
    const searchParams = streamUrl.searchParams

    // re-structure search parameters for SIGV4
    for (const [k,v] of searchParams) {      
        params[k] = v        
    }

    const request = new HttpRequest({
        hostname: streamUrl.hostname,
        method: 'GET',
        protocol: streamUrl.protocol,
        path: streamUrl.pathname,         
        query: params,
        port: 443,
        headers: {
            'Content-Type': 'text/plain',
            host: streamUrl.hostname, // compulsory for sigv4
        },
    })
    
    const signedRequest = await signer.sign(request)    
    const { headers, body, method } = signedRequest

    const res = await fetch(streamUrl, {
        headers, 
        body,
        method,
    }).catch((err) => {
        console.log(err)
        throw new Error(err);
    });
    
    if (res.ok){
        const result = await streamToString(res.body)       
        console.log("final result:")
        console.log(result)
    } else {
        console.log("error calling streaming lambda:", res.status, res.statusText)
    }

})();
