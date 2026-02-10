import json
import os
import boto3
import time
import traceback

# Initialize Bedrock client
bedrock_runtime = boto3.client('bedrock-runtime')

def lambda_handler(event, context):
    # Extract the AWS question
    query = event['query']
    agent_id = event.get('agent_id', 'default')
    approach = event.get('approach', 'general')
    
    print(f"Processing query: {query} with approach: {approach}")
    
    # First, try to get answer from MCP server with specialized search
    mcp_info = query_mcp_server(query, approach)
    
    if mcp_info:
        # Use MCP server response directly but format based on approach
        print("Using MCP server response directly")
        
        # Format the MCP response based on agent's approach
        if approach == 'service_specific':
            result = f"Based on AWS Documentation (Service Implementation Focus):\n\n{mcp_info}"
        elif approach == 'architecture_patterns':
            result = f"Based on AWS Documentation (Architecture & Design Focus):\n\n{mcp_info}"
        elif approach == 'cost_optimization':
            result = f"Based on AWS Documentation (Cost & Pricing Focus):\n\n{mcp_info}"
        else:
            result = f"Based on AWS Documentation (General Overview):\n\n{mcp_info}"
            
        confidence_score = 0.95  # High confidence for official documentation
        
        return {
            'agent_id': agent_id,
            'approach': approach,
            'query': query,
            'result': result,
            'confidence_score': confidence_score,
            'processing_time': time.time() - context.get_remaining_time_in_millis()/1000,
            'services_referenced': extract_aws_services(result),
            'source': 'mcp_server',
            'lambda_execution_arn': context.aws_request_id
        }
    
    # Fallback to Bedrock if MCP server doesn't have the information
    print("MCP server didn't provide results, falling back to Bedrock")
    
    # Create a customized prompt based on the agent's assigned approach
    if approach == 'service_specific':
        prompt = f"""You are an AWS service specialist.
        Provide a step-by-step guide on how to accomplish this task on AWS:
        {query}
        
        Focus on the specific AWS services needed, their configurations, and how they interact.
        Include console instructions and any relevant CLI commands or CloudFormation snippets.
        Include confidence score from 0-1 at the end of your response.
        """
    elif approach == 'architecture_patterns':
        prompt = f"""You are an AWS solutions architect.
        Provide an architectural solution for this AWS implementation question:
        {query}
        
        Focus on best practice architectural patterns, service selection rationale, and design considerations.
        Include a logical architecture description and service interactions.
        Include confidence score from 0-1 at the end of your response.
        """
    elif approach == 'cost_optimization':
        prompt = f"""You are an AWS cost optimization specialist.
        For the following AWS implementation question:
        {query}
        
        Provide a cost-effective approach, pricing considerations, and optimization strategies.
        Include relevant pricing models, reserved capacity options, and cost comparison of alternatives.
        Include confidence score from 0-1 at the end of your response.
        """
    else:
        prompt = f"""You are an AWS technical expert.
        Provide a comprehensive answer to the following AWS implementation question:
        {query}
        
        Include relevant AWS services, implementation steps, and best practices.
        Include confidence score from 0-1 at the end of your response.
        """
    
    try:
        # Invoke Bedrock model
        model_id = os.environ.get('MODEL_ID', 'us.anthropic.claude-3-5-haiku-20241022-v1:0')
        print(f"Invoking Bedrock model: {model_id}")
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2,
                "top_p": 0.9
            })
        )
        
        # Parse response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        result = response_body.get('content', [{}])[0].get('text', '')
        
        # Extract confidence score
        try:
            if 'confidence score:' in result.lower():
                confidence_parts = result.lower().split('confidence score:')
                confidence_score = float(confidence_parts[1].strip())
            else:
                import re
                matches = re.findall(r'confidence(?:\s*(?:score|level|rating)?)?(?:\s*[:=]\s*)?([0-9]*\.?[0-9]+)', 
                                    result.lower())
                confidence_score = float(matches[-1]) if matches else 0.7
        except Exception:
            confidence_score = 0.7
        
        return {
            'agent_id': agent_id,
            'approach': approach,
            'query': query,
            'result': result,
            'confidence_score': confidence_score,
            'processing_time': time.time() - context.get_remaining_time_in_millis()/1000,
            'services_referenced': extract_aws_services(result),
            'source': 'bedrock',
            'lambda_execution_arn': context.aws_request_id
        }
        
    except Exception as e:
        print(f"Error invoking Bedrock: {str(e)}")
        return {
            'agent_id': agent_id,
            'approach': approach,
            'query': query,
            'result': f"Error processing query: {query}. Please try again.",
            'confidence_score': 0.1,
            'processing_time': time.time() - context.get_remaining_time_in_millis()/1000,
            'services_referenced': [],
            'source': 'error',
            'lambda_execution_arn': context.aws_request_id
        }

def query_mcp_server(query, approach):
    """Use the AWS Documentation MCP Server Lambda with approach-specific search strategies"""
    try:
        print(f"Querying MCP server for: {query} with approach: {approach}")
        
        # Create approach-specific search phrases
        if approach == 'service_specific':
            # Focus on implementation, configuration, setup
            search_phrase = f"{query} implementation configuration setup guide"
        elif approach == 'architecture_patterns':
            # Focus on architecture, design, patterns, best practices
            search_phrase = f"{query} architecture design patterns best practices"
        elif approach == 'cost_optimization':
            # Focus on pricing, cost, billing, optimization
            search_phrase = f"{query} pricing cost optimization billing"
        else:
            # General search
            search_phrase = query
        
        print(f"Using specialized search phrase: {search_phrase}")
        
        # Create a Lambda client
        lambda_client = boto3.client('lambda')
        
        # Create the MCP request with specialized search
        mcp_request = {
            "action": "search",
            "search_phrase": search_phrase,
            "limit": 5
        }
        
        # Invoke the MCP server Lambda
        response = lambda_client.invoke(
            FunctionName=os.environ.get('MCP_FUNCTION_NAME', 'AWSMCPServerFunction'),
            InvocationType='RequestResponse',
            Payload=json.dumps(mcp_request)
        )
        
        # Parse the response
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"MCP server response received for {approach} approach")
        
        # Check for errors
        if 'error' in payload:
            print(f"Error from MCP server: {payload['error']}")
            return ""
        
        # Process the search results
        if 'output' in payload and 'content' in payload['output']:
            content = json.loads(payload['output']['content'])
            
            # Extract the top search results
            results = []
            for item in content:
                if isinstance(item, dict) and 'url' in item and 'title' in item and 'context' in item:
                    results.append(f"# {item['title']}\n\n{item['context']}\n\nSource: {item['url']}")
            
            # If we have results, return them
            if results:
                print(f"Found {len(results)} MCP results for {approach} approach")
                return "\n\n".join(results)
        
        print(f"No MCP content found for {approach} approach")
        return ""
            
    except Exception as e:
        print(f"Error querying MCP server: {str(e)}")
        print(traceback.format_exc())
        return ""

def extract_aws_services(text):
    """Extract mentioned AWS services from the response"""
    aws_services = [
        "EC2", "S3", "Lambda", "DynamoDB", "RDS", "Aurora", "ECS", "EKS",
        "SQS", "SNS", "API Gateway", "CloudFormation", "CloudFront", "Route 53",
        "VPC", "IAM", "CloudWatch", "Step Functions", "EventBridge", "Cognito",
        "Kinesis", "Glue", "Athena", "Redshift", "EMR", "SageMaker"
    ]
    
    found_services = []
    for service in aws_services:
        if service in text or service.lower() in text.lower():
            found_services.append(service)
    
    return found_services
