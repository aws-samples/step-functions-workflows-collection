import json
import boto3
import os
import traceback

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")  # Log the input for debugging
    
    try:
        # Initialize Bedrock client
        bedrock_runtime = boto3.client('bedrock-runtime')
        
        # Extract the original query from the event
        original_query = event.get('original_query', 'How to implement on AWS?')
        
        # Extract results from multiple agents
        agent_results = event.get('agent_results', [])
        
        # Consolidate mentioned AWS services across all agents
        all_services = set()
        for result in agent_results:
            if isinstance(result, dict):
                services = result.get('services_referenced', [])
                if isinstance(services, list):
                    all_services.update(services)
        
        # Prepare a synthesis prompt
        results_text = ""
        for i, result in enumerate(agent_results):
            if isinstance(result, dict):
                approach = result.get('approach', 'general')
                confidence = result.get('confidence_score', 'unknown')
                result_text = result.get('result', '')
                if not result_text and 'body' in result:
                    # Try to extract from body if result is empty
                    try:
                        body = result['body']
                        if body.startswith('"') and body.endswith('"'):
                            body = body[1:-1]  # Remove quotes
                        result_text = body
                    except:
                        result_text = "No result available"
                
                results_text += f"Agent {i+1} ({approach}, confidence: {confidence}):\n"
                results_text += f"{result_text}\n\n"
        
        synthesis_prompt = f"""You are an AWS solutions architect synthesizer.
        The original question was: "{original_query}"
        
        Below are different perspectives from multiple AWS experts on how to implement this solution.
        Please synthesize these results into a comprehensive answer.
        
        {results_text}
        
        Provide a synthesized solution that:
        1. Begins with a clear architectural overview
        2. Includes the most appropriate AWS services from all responses
        3. Provides step-by-step implementation guidance
        4. Highlights best practices and security considerations
        5. Mentions cost optimization strategies
        
        Focus on creating actionable guidance that an AWS customer could follow.
        """
        
        # Invoke Bedrock for synthesis
        response = bedrock_runtime.invoke_model(
            modelId=os.environ.get('MODEL_ID', 'us.anthropic.claude-3-5-haiku-20241022-v1:0'),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 3000,
                "messages": [
                    {
                        "role": "user",
                        "content": synthesis_prompt
                    }
                ],
                "temperature": 0.3,
                "top_p": 0.9
            })
        )
        
        # Parse response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        synthesized_result = response_body.get('content', [{}])[0].get('text', '')
        
        # Extract AWS services mentioned in the synthesized result
        services_mentioned = extract_aws_services(synthesized_result)
        if not services_mentioned:
            services_mentioned = list(all_services)
        
        return {
            'synthesized_result': synthesized_result,
            'source_count': len(agent_results),
            'services_mentioned': services_mentioned,
            'original_query': original_query
        }
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        print(traceback.format_exc())
        # Fallback response if anything fails
        return {
            'synthesized_result': f"I encountered an error while processing your request about {original_query if 'original_query' in locals() else 'your query'}. Please try again.",
            'source_count': 0,
            'services_mentioned': [],
            'original_query': original_query if 'original_query' in locals() else "Unknown query"
        }

def extract_aws_services(text):
    """Extract mentioned AWS services from the response"""
    aws_services = [
        "EC2", "S3", "Lambda", "DynamoDB", "RDS", "Aurora", "ECS", "EKS",
        "SQS", "SNS", "API Gateway", "CloudFormation", "CloudFront", "Route 53",
        "VPC", "IAM", "CloudWatch", "Step Functions", "EventBridge", "Cognito",
        "Kinesis", "Glue", "Athena", "Redshift", "EMR", "SageMaker", "Bedrock"
    ]
    
    found_services = []
    for service in aws_services:
        if service in text or service.lower() in text.lower():
            found_services.append(service)
    
    return found_services
