import json
import os
import boto3

def lambda_handler(event, context):
    # Extract the confidence threshold from environment variables
    confidence_threshold = float(os.environ.get('CONFIDENCE_THRESHOLD', 0.8))
    
    # Get the result from the worker agent
    agent_result = event
    confidence_score = agent_result.get('confidence_score', 0)
    
    # Additional AWS-specific evaluation criteria
    aws_service_completeness = evaluate_service_completeness(
        agent_result.get('query', ''), 
        agent_result.get('result', ''),
        agent_result.get('services_referenced', [])
    )
    
    has_implementation_steps = 'steps' in agent_result.get('result', '').lower() or \
                              'step 1' in agent_result.get('result', '').lower()
    
    # Adjust confidence score based on AWS-specific criteria
    adjusted_score = confidence_score
    if aws_service_completeness > 0.8:
        adjusted_score += 0.1
    if has_implementation_steps:
        adjusted_score += 0.05
        
    adjusted_score = min(adjusted_score, 1.0)  # Cap at 1.0
    
    # Determine if the confidence threshold is met
    threshold_met = adjusted_score >= confidence_threshold
    
    # If threshold is met, we will stop other executions
    if threshold_met:
        # In production, extract and stop the parent Map execution
        execution_arn = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'unknown')
        stop_other_executions(execution_arn)
    
    return {
        'result': agent_result['result'],
        'confidence_score': adjusted_score,
        'original_confidence': confidence_score,
        'threshold_met': threshold_met,
        'agent_id': agent_result.get('agent_id', 'unknown'),
        'aws_service_completeness': aws_service_completeness,
        'has_implementation_steps': has_implementation_steps
    }

def evaluate_service_completeness(query, result, services_referenced):
    """Evaluate if the result references appropriate AWS services for the query"""
    # Simple heuristic - could be enhanced with ML-based evaluation
    compute_keywords = ['compute', 'server', 'instance', 'container', 'serverless']
    storage_keywords = ['storage', 'file', 'object', 'backup']
    database_keywords = ['database', 'table', 'query', 'record', 'data store']
    network_keywords = ['network', 'vpc', 'subnet', 'traffic', 'routing']
    
    expected_services = []
    
    # Determine expected service types based on query
    query_lower = query.lower()
    if any(keyword in query_lower for keyword in compute_keywords):
        expected_services.extend(['EC2', 'Lambda', 'ECS', 'EKS', 'Fargate'])
    if any(keyword in query_lower for keyword in storage_keywords):
        expected_services.extend(['S3', 'EBS', 'EFS', 'FSx', 'Storage Gateway'])
    if any(keyword in query_lower for keyword in database_keywords):
        expected_services.extend(['RDS', 'DynamoDB', 'Aurora', 'DocumentDB', 'Neptune'])
    if any(keyword in query_lower for keyword in network_keywords):
        expected_services.extend(['VPC', 'Route 53', 'CloudFront', 'API Gateway'])
    
    # If no specific service type is identified, return medium score
    if not expected_services:
        return 0.7
        
    # Calculate overlap between expected and referenced services
    service_overlap = len(set([s.upper() for s in services_referenced]) & 
                          set([s.upper() for s in expected_services]))
                          
    if service_overlap == 0:
        return 0.5
    
    # Calculate completeness score
    return min(1.0, service_overlap / (len(expected_services) * 0.7))

def stop_other_executions(execution_arn):
    """Stop other parallel executions when threshold is met"""
    # In a real implementation, you would:
    # 1. Extract the execution ID from context
    # 2. Use Step Functions API to stop the Map state executions
    
    # Example implementation with AWS SDK:
    try:
        # This is a simplified example - in production, you'd need to 
        # properly extract the execution ARN from the context
        sfn_client = boto3.client('stepfunctions')
        sfn_client.stop_execution(
            executionArn=execution_arn,
            cause="Confidence threshold met by another agent"
        )
        print(f"Successfully stopped execution: {execution_arn}")
    except Exception as e:
        print(f"Error stopping execution: {str(e)}")
