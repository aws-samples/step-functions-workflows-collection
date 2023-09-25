const { CloudFormationClient, DescribeStacksCommand } = require('@aws-sdk/client-cloudformation');
const { HttpRequest } = require('@aws-sdk/protocol-http')
const { defaultProvider } = require('@aws-sdk/credential-provider-node')
const { SignatureV4 } = require('@aws-sdk/signature-v4')
const { Sha256 } = require('@aws-crypto/sha256-browser')

const region = process.env.AWS_REGION;
const cfClient = new CloudFormationClient({ region: region });
var apiEndpoint;

const test_timeout_ms = 80000;
const expected_number_of_results = 5;

async function getApiEndpoint() {
    const stackName = process.env.AWS_SAM_STACK_NAME;

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

async function signURL(urlToSign) {
    
    const signer = new SignatureV4({
        credentials: defaultProvider(),
        region: region,
        service: 'lambda',
        sha256: Sha256
    })

    const apiUrl = new URL(urlToSign)
    var params = {}
    const searchParams = apiUrl.searchParams

    // re-structure search parameters for SIGV4
    for (const [k,v] of searchParams) {      
        params[k] = v        
    }
    
    const request = new HttpRequest({
        hostname: apiUrl.hostname,
        method: 'GET',
        protocol: apiUrl.protocol,
        path: apiUrl.pathname,         
        query: params,
        port: 443,
        headers: {
            'Content-Type': 'application/json',
            host: apiUrl.hostname, // compulsory
        },
    })

    const signedRequest = await signer.sign(request)
    const { headers, body, method } = signedRequest
    return {
        apiUrl: apiUrl,
        headers: headers,
        body: body,
        method: method
    }
}

async function verifyResponseStream(stream, expectedResults) {
    const chunks = [];
    var i = 0;
    for await (const chunk of stream) {
        const buf = Buffer.from(chunk);
        // a single result or both results can be streamed in the same buffer        
        const sbuf = buf.toString("utf-8").split('\n').slice(0, -1);                                    
        for (const bufLine of sbuf){
            var jbuf;
            try {
                var jbuf = JSON.parse(bufLine);
            } catch (err) {
                console.log(err);
                throw new Error(err);
            }
            expect(jbuf).toBeDefined();    
            const expectedResultObj = expectedResults[i];            
            expect(jbuf).toEqual(expect.objectContaining(expectedResultObj));
            i++;
        }
        chunks.push(buf);            
    }
    
    return Buffer.concat(chunks).toString("utf-8");
}

async function testWorkflow() {
    if (!apiEndpoint) {
        apiEndpoint = await getApiEndpoint();
    }

    const apiResponse = await fetch(apiEndpoint, {
        method: 'POST'         
    }).catch((err) => {
        throw new Error(err);
    });

    expect(apiResponse.ok).toBeTruthy();
    const apiJsonResponse = await apiResponse.json();
    expect(apiJsonResponse).toBeDefined();
    expect(apiJsonResponse).toHaveProperty("workflow")
    expect(apiJsonResponse.workflow).toEqual(expect.objectContaining({
        executionArn: expect.stringMatching("arn:aws:states:.*"),
        lambdaResultURL: expect.any(String),
        completeLambdaResultURL: expect.any(String),
        startDate: expect.any(String)
    }));

    resultStreamingLambdaUrl = apiJsonResponse.workflow.completeLambdaResultURL;
    
    const { apiUrl: streamUrl, headers, body, method } = await signURL(resultStreamingLambdaUrl)
    const lambdaResponse = await fetch(streamUrl, {
        headers, 
        body,
        method,
    }).catch((err) => {
        throw new Error(err);        
    });

    expect(lambdaResponse.ok).toBeTruthy();
    
    const expectedResults = [];
    
    for (let index = 0; index < expected_number_of_results; index++) {
        const element = {
            Result: `This is simulated result ${index}`,
            ExecutionArn: expect.stringMatching("ExampleWorkflow.*"),
            ResultTimestamp: expect.any(String)
        };

        if (index === expected_number_of_results - 1) {
            element.FinalResult = true;
        }
        expectedResults.push(element);
    }   
    
    const completeResult = await verifyResponseStream(
        lambdaResponse.body,         
        expectedResults
    )
    // verify we got both results
    const lines = completeResult.trim().split("\n");
    expect(lines.length).toEqual(expected_number_of_results);
}

describe('Test Async Results notification for a single invocation', () => {    
    test('get async notifications for a single invocation of an express workflow', testWorkflow, test_timeout_ms);
});

const numberConcurrentTests = 10;
describe('Test Async results notification for multiple invocations', () => { 
    var inputs = Array(numberConcurrentTests).fill(null);
    test.concurrent.each(inputs)('test %# : get async notifications for an express workflow', testWorkflow, test_timeout_ms);
});
