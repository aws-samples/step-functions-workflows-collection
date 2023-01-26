 
/*  
SPDX-FileCopyrightText: 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0 

A Lambda function code that uses axios to send API requests to GitHub traffic API to get daily views on a GitHub repository
The function uses SSM parameter store to retrieve GitHub Personal Access Token
The Personal Access Token is used to authenticate API requests to GitHub
The function is invoked by Amazon EventBridge Scheduler rule to get daily views for a GitHub repository
in nodejs 18.x runtime
*/

const axios = require('axios');
const { SSMClient, GetParameterCommand } = require("@aws-sdk/client-ssm")

exports.handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));

    const githubToken = await getGitHubToken();
    let response = await getViews(githubToken, event.repoName);
    
    //return the last element of the array
    response.data.views[response.data.views.length - 2].repoName=event.repoName
    return response.data.views[response.data.views.length - 2];
}

async function getGitHubToken() {
    const client = new SSMClient();
    const command = new GetParameterCommand({Name: process.env.SSM});
    const response = await client.send(command);
    return response.Parameter.Value;
}
async function getViews(githubToken, repoName) {
    const response = await axios.get(`https://api.github.com/repos/${repoName}/traffic/views`, {
        headers: {
            'Authorization': `token ${githubToken}`
        }
    });
    return response;
}



