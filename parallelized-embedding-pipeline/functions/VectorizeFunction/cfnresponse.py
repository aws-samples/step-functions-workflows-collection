# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import urllib.request

SUCCESS = "SUCCESS"
FAILED = "FAILED"

def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=None):
    responseUrl = event['ResponseURL']

    logging.debug("CFN response URL: " + responseUrl)

    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = reason or ('See CloudWatch Log Stream: ' + context.log_stream_name)
    responseBody['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['NoEcho'] = noEcho
    responseBody['Data'] = responseData

    json_responseBody = json.dumps(responseBody)
    logging.debug("CFN Response body: " + json_responseBody)

    headers = {
        'content-type': '',
        'content-length': str(len(json_responseBody))
    }

    try:
        # Validate URL scheme
        parsed_url = urllib.parse.urlparse(responseUrl)
        if parsed_url.scheme not in ['http', 'https']:
            raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}")
        
        # Create and send request
        req = urllib.request.Request(responseUrl,
                                   data=json_responseBody.encode('utf-8'),
                                   headers=headers,
                                   method='PUT')
        
        # Use a context manager with timeout
        with urllib.request.urlopen(req, timeout=30) as response:
            print(response.read().decode('utf-8'))
        logging.debug("CFN response sent successfully")
    except Exception as e:
        logging.error("Failed to send CFN response: " + str(e))
