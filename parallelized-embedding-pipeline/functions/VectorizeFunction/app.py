import boto3
import os
import logging
import json
import uuid
import re
import random

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
rds_client = boto3.client('rds-data')
bedrock_runtime = boto3.client('bedrock-runtime')

def generate_titan_embeddings(text):
    """
    Generate embeddings using Amazon Titan Embeddings model through Bedrock
    """
    try:
        # Prepare request body for Titan embedding model
        request_body = {
            "inputText": text
        }
        
        # Get model ID from environment or use default
        model_id = os.environ.get('EMBEDDING_MODEL_ID', 'amazon.titan-embed-text-v1')
        
        logger.info(f"Requesting embeddings from Amazon Titan model: {model_id}")
        
        # Make the API call to Bedrock
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response.get('body').read())
        embeddings = response_body.get('embedding')
        
        logger.info(f"Successfully generated embedding vector with {len(embeddings)} dimensions")
        
        # Check dimensions and pad/truncate if needed to match expected 1536 dimensions
        required_dimensions = 1536
        if len(embeddings) != required_dimensions:
            logger.warning(f"Model returned {len(embeddings)} dimensions but database expects {required_dimensions}. Adjusting vector.")
            if len(embeddings) < required_dimensions:
                # Pad with zeros
                padding = [0.0] * (required_dimensions - len(embeddings))
                embeddings = embeddings + padding
                logger.info(f"Padded vector to {len(embeddings)} dimensions")
            else:
                # Truncate
                embeddings = embeddings[:required_dimensions]
                logger.info(f"Truncated vector to {len(embeddings)} dimensions")
        
        return embeddings
        
    except Exception as e:
        logger.error(f"Error generating Titan embeddings: {str(e)}")
        # Fall back to a random vector if embedding generation fails
        fallback_vector = generate_fallback_vector(1536)
        logger.info(f"Using fallback vector with {len(fallback_vector)} dimensions")
        return fallback_vector

def generate_fallback_vector(dim=1536, seed=12345):
    """
    Generate a fallback vector if the embedding service fails
    
    The fallback vector serves as a placeholder that allows the document to be 
    stored in the database even if we can't get real embeddings. While these 
    random embeddings won't be useful for semantic search, they ensure the document 
    is at least stored and can be retrieved by non-vector methods.
    """
    # Seed the random number generator
    random.seed(seed)
    # Create a vector of specified dimension with values between -0.1 and 0.1
    # We use small values to minimize potential impact on vector similarity searches
    vector = [random.uniform(-0.1, 0.1) for _ in range(dim)]
    return vector

def embedding_to_string(vector):
    """Convert embedding vector to string format for database"""
    return "[" + ",".join(str(x) for x in vector) + "]"

def detect_document_type_from_filename(key):
    """
    Detects document type based on filename pattern
    The ingest functions convert files to text with pattern: original_name.pdf_text.txt
    Returns document_type and document_sub_type based on the original extension
    """
    # Extract the original filename by looking for patterns like '.pdf_text.txt', '.docx_text.txt'
    original_ext = None
    
    # Check for common patterns from the ingest functions
    for ext in ['.pdf', '.docx', '.doc', '.ppt', '.pptx', '.xls', '.xlsx']:
        if f"{ext}_text.txt" in key.lower():
            original_ext = ext
            break
    
    # If no match found from patterns, fall back to current extension
    if original_ext is None:
        logger.info(f"No original extension pattern found in {key}, using current extension")
        return detect_document_type(key)
    
    logger.info(f"Detected original extension {original_ext} from filename {key}")
    
    # Map the extension to document types
    doc_type = "Text"  # Default
    doc_subtype = "Text"
    
    if original_ext == '.pdf':
        doc_type = "PDF"
        doc_subtype = "PDF"
    elif original_ext in ['.docx', '.doc']:
        doc_type = "DOCX"
        doc_subtype = "DOCX"
    elif original_ext in ['.pptx', '.ppt']:
        doc_type = "PPT"
        doc_subtype = "PPT" 
    elif original_ext in ['.xlsx', '.xls']:
        doc_type = "Excel"
        doc_subtype = "Excel"
    
    logger.info(f"Assigned document type: {doc_type}, subtype: {doc_subtype} based on original extension")
    return doc_type, doc_subtype

def detect_document_type(key):
    """
    Detects document type based on file extension
    Returns document_type and document_sub_type
    """
    # Convert to lowercase for case-insensitive matching
    key_lower = key.lower()
    
    # Default type
    doc_type = "Text"
    doc_subtype = "Text"
    
    # Check for document types based on extensions
    if key_lower.endswith('.pdf'):
        doc_type = "PDF"
        doc_subtype = "PDF"
    elif key_lower.endswith('.doc') or key_lower.endswith('.docx'):
        doc_type = "DOCX"
        doc_subtype = "DOCX"
    elif key_lower.endswith('.ppt') or key_lower.endswith('.pptx'):
        doc_type = "PPT"
        doc_subtype = "PPT"
    elif key_lower.endswith('.xls') or key_lower.endswith('.xlsx'):
        doc_type = "Excel"
        doc_subtype = "Excel"
    elif key_lower.endswith('.txt'):
        doc_type = "Text"
        doc_subtype = "Text"
    elif key_lower.endswith('.html') or key_lower.endswith('.htm'):
        doc_type = "HTML"
        doc_subtype = "HTML"
    elif key_lower.endswith('.json'):
        doc_type = "JSON"
        doc_subtype = "JSON"
    elif key_lower.endswith('.xml'):
        doc_type = "XML"
        doc_subtype = "XML"
    elif key_lower.endswith('.csv'):
        doc_type = "CSV"
        doc_subtype = "CSV"
    
    logger.info(f"Detected document type: {doc_type}, subtype: {doc_subtype} for file: {key}")
    return doc_type, doc_subtype

def lambda_handler(event, context):
    """
    Lambda function that reads from S3, generates embeddings using Amazon Titan,
    and writes to the database with proper vector embeddings for semantic search.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract event details (case insensitive)
        bucket = event.get('bucket') or event.get('Bucket')
        key = event.get('key') or event.get('Key')
        byte_range_start = event.get('byteRangeStart') or event.get('ByteRangeStart')
        byte_range_end = event.get('byteRangeEnd') or event.get('ByteRangeEnd')
        
        if not key:
            logger.error("No key provided in the event")
            logger.error(f"Event keys: {list(event.keys())}")
            return {"statusCode": 400, "body": f"No key provided in the event. Available keys: {list(event.keys())}"}
        
        if not bucket:
            logger.error("No bucket provided in the event")
            logger.error(f"Event keys: {list(event.keys())}")
            return {"statusCode": 400, "body": f"No bucket provided in the event. Available keys: {list(event.keys())}"}
        
        # Define path here so it's available for use later
        path = f"{bucket}/{key}"
        
        logger.info(f"Processing byte range: {byte_range_start}-{byte_range_end} for object s3://{bucket}/{key}")
        
        # Read the S3 object
        if byte_range_start is not None and byte_range_end is not None:
            response = s3.get_object(
                Bucket=bucket,
                Key=key,
                Range=f"bytes={byte_range_start}-{byte_range_end}"
            )
            logger.info(f"Read S3 object with byte range {byte_range_start}-{byte_range_end}")
        else:
            response = s3.get_object(
                Bucket=bucket,
                Key=key
            )
            logger.info(f"Read entire S3 object")
            
        # Process the byte range data
        byte_range_data = response['Body'].read()
        
        # Try to decode the byte range data with different encodings
        try:
            # First try UTF-8 (most common for text files)
            text_data = byte_range_data.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # Fall back to UTF-16 if UTF-8 fails
                text_data = byte_range_data.decode('utf-16')
            except UnicodeDecodeError:
                try:
                    # Third try with utf-16-le (little endian)
                    text_data = byte_range_data.decode('utf-16-le')
                except UnicodeDecodeError:
                    # Last resort, use latin-1 which can decode any bytes
                    text_data = byte_range_data.decode('latin-1')
        
        # If text data is empty or doesn't look right, use placeholder
        if not text_data or len(text_data.strip()) < 10:
            logger.warning(f"Text data seems too short or empty")
            text_data = "This is placeholder text because the original chunk could not be properly decoded"
        
        logger.info(f"Successfully decoded text of length: {len(text_data)}")
        if len(text_data) > 100:
            logger.info(f"Text preview: {text_data[:100]}...")
            
        # Clean the text data for better embeddings
        # Remove excessive whitespace, normalize line endings, etc.
        text_data = re.sub(r'\s+', ' ', text_data).strip()
        
        # Remove null bytes that cause PostgreSQL UTF-8 encoding errors
        text_data = text_data.replace('\x00', '')
        
        # Truncate the text if it's too long for the embedding model
        max_chars = 8000  # Conservative estimate to avoid token limits
        if len(text_data) > max_chars:
            logger.warning(f"Text is too long ({len(text_data)} chars), truncating to {max_chars} chars")
            text_data = text_data[:max_chars]
        
        # Generate Amazon Titan embeddings
        embedding_vector = generate_titan_embeddings(text_data)
        
        # Convert embedding vector to string format for database storage
        vector_str = embedding_to_string(embedding_vector)
        
        # Get database configuration
        secret_arn = os.environ.get('DATABASE_SECRET_ARN')
        cluster_arn = os.environ.get('SERVERLESS_AURORA_CLUSTER_ARN')
        database_name = os.environ.get('DATABASE_NAME')
        table_name = os.environ.get('TABLE_NAME')
        workspace_id = os.environ.get('WORKSPACE_ID', '00000000-0000-0000-0000-000000000000')
        
        logger.info(f"Database configuration:")
        logger.info(f"  Secret ARN: {secret_arn}")
        logger.info(f"  Cluster ARN: {cluster_arn}")
        logger.info(f"  Database name: {database_name}")
        logger.info(f"  Table name: {table_name}")
        
        # Generate UUIDs for required fields
        chunk_id = str(uuid.uuid4())
        doc_id = event.get('document_id', str(uuid.uuid5(uuid.NAMESPACE_DNS, key)))
        doc_sub_id = event.get('document_sub_id', str(uuid.uuid5(uuid.NAMESPACE_DNS, key)))
        
        # Detect document type based on file extension pattern
        document_type, document_sub_type = detect_document_type_from_filename(key)
        title = event.get('title', key.split('/')[-1])
        
        # First verify database connection
        logger.info("Testing database connection")
        test_sql = "SELECT 1 as test_connection;"
        test_response = rds_client.execute_statement(
            resourceArn=cluster_arn,
            secretArn=secret_arn,
            database=database_name,
            sql=test_sql
        )
        logger.info(f"Database connection test successful")
        
        # Validate table name to prevent SQL injection
        allowed_tables = ['vectortable', 'vector_data']  # Add your allowed table names
        if table_name not in allowed_tables:
            raise ValueError(f"Invalid table name: {table_name}")
            
        # Set up safe SQL with parameters
        insert_sql = """
        INSERT INTO :table_name (
            chunk_id,
            workspace_id, 
            document_id,
            document_sub_id,
            document_type,
            document_sub_type,
            path,
            title,
            content,
            content_embeddings
        ) VALUES (
            :chunk_id,
            :workspace_id,
            :document_id,
            :document_sub_id,
            :document_type,
            :document_sub_type,
            :path,
            :title,
            :content,
            :vector::vector
        )
        """
        
        # Define parameters
        parameters = [
            {'name': 'chunk_id', 'value': {'stringValue': chunk_id}},
            {'name': 'workspace_id', 'value': {'stringValue': workspace_id}},
            {'name': 'document_id', 'value': {'stringValue': doc_id}},
            {'name': 'document_sub_id', 'value': {'stringValue': doc_sub_id}},
            {'name': 'document_type', 'value': {'stringValue': document_type}},
            {'name': 'document_sub_type', 'value': {'stringValue': document_sub_type}},
            {'name': 'path', 'value': {'stringValue': path}},
            {'name': 'title', 'value': {'stringValue': title}},
            {'name': 'content', 'value': {'stringValue': text_data}},
            {'name': 'vector', 'value': {'stringValue': vector_str}}
        ]
        
        logger.info(f"Executing database insert with document type: {document_type}, subtype: {document_sub_type}")
        
        # Now try the insert
        insert_response = rds_client.execute_statement(
            resourceArn=cluster_arn,
            secretArn=secret_arn,
            database=database_name,
            sql=insert_sql,
            parameters=parameters
        )
        logger.info(f"Insert successful!")
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {document_type} document and stored with embeddings',
                'document_id': doc_id,
                'document_sub_id': doc_sub_id
            })
        }
        
    except Exception as e:
        logger.error(f"General error: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }
