import boto3
import json
import time
import argparse

def test_bedrock_embedding(text="This is a test sentence to check if the Bedrock API is working properly.", model_id="amazon.titan-embed-text-v1", region=None):
    """
    Test the Bedrock embedding API with a simple text
    """
    print(f"Testing Bedrock API with model: {model_id}")
    print(f"Input text: {text}")
    
    if region:
        print(f"Using region: {region}")
    
    start_time = time.time()
    
    # Create a Bedrock Runtime client
    bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
    
    try:
        # Prepare the request body for the embedding model
        request_body = {
            "inputText": text
        }
        
        print("Calling Bedrock API...")
        
        # Make the API call to Bedrock
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        
        # Different models might have different response formats
        embeddings = response_body.get('embedding', 
                    response_body.get('embeddings', 
                    response_body.get('vector', [])))
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"API call successful! Duration: {duration:.2f} seconds")
        print(f"Embedding dimensions: {len(embeddings)}")
        print(f"First 5 values: {embeddings[:5]}")
        
        return True
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Error after {duration:.2f} seconds: {str(e)}")
        print("This suggests an issue with AWS Bedrock access.")
        print("Make sure:")
        print("1. The Bedrock model is enabled in your AWS account")
        print("2. Your AWS credentials have permission to access Bedrock")
        print("3. The model ID is correct")
        print("4. You're in a region where the model is available")
        
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the AWS Bedrock embedding API")
    parser.add_argument("--model", default="amazon.titan-embed-text-v1", help="Bedrock model ID to test")
    parser.add_argument("--text", default="This is a test sentence for the Bedrock API.", help="Text to embed")
    parser.add_argument("--region", help="AWS region to use")
    
    args = parser.parse_args()
    test_bedrock_embedding(args.text, args.model, args.region)
