import boto3
import json
import logging
import time
import os
import cfnresponse

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
rds_client = boto3.client('rds-data')
secretsmanager = boto3.client('secretsmanager')

def lambda_handler(event, context):
    """Handle CloudFormation custom resource for initializing the database"""
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Get parameters from environment 
    cluster_arn = os.environ['CLUSTER_ARN']
    secret_arn = os.environ['SECRET_ARN']
    database_name = os.environ['DATABASE_NAME']
    table_name = os.environ['TABLE_NAME']
    
    # Check if this is a direct invocation (not from CloudFormation)
    if not event or ('RequestType' not in event):
        logger.info("Direct invocation detected - running database initialization directly")
        try:
            # Run database initialization directly
            success = init_database(cluster_arn, secret_arn, database_name, table_name, context)
            return {
                "statusCode": 200 if success else 500,
                "body": "Database initialization successful" if success else "Database initialization failed or timed out"
            }
        except Exception as e:
            logger.error(f"Error during direct invocation: {str(e)}")
            return {
                "statusCode": 500,
                "body": f"Error: {str(e)}"
            }
    
    # Normal CloudFormation invocation flow
    response_data = {"Message": "Operation completed"}
    response_status = cfnresponse.SUCCESS
    
    try:
        request_type = event.get('RequestType')
        if request_type == 'Create' or request_type == 'Update':
            # Initialize the database
            if init_database(cluster_arn, secret_arn, database_name, table_name, context):
                response_data = {"Message": "Database initialized successfully"}
            else:
                # If init_database returned False, it means we're approaching timeout
                # Lambda will be re-invoked by CloudFormation
                response_data = {"Message": "Database initialization in progress, will retry"}
        
        elif request_type == 'Delete':
            # For delete operations, just acknowledge the request immediately
            # No specific cleanup needed for the database
            logger.info("Delete request received, immediately acknowledging")
            response_data = {"Message": "Resource deletion acknowledged"}
        
        else:
            logger.warning(f"Unknown RequestType: {request_type}")
            response_data = {"Message": f"Unknown or missing request type: {request_type}"}
    
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        response_status = cfnresponse.FAILED
        response_data = {"Error": str(e)}
    
    # Send response to CloudFormation (only if ResponseURL is in the event)
    if 'ResponseURL' in event:
        try:
            logger.info(f"Sending response to CloudFormation: {response_status}, {response_data}")
            cfnresponse.send(event, context, response_status, response_data)
        except Exception as send_error:
            logger.error(f"Failed to send response to CloudFormation: {str(send_error)}")
    else:
        logger.warning("No ResponseURL found in event, skipping CloudFormation response")
        
    return {
        "statusCode": 200 if response_status == cfnresponse.SUCCESS else 500,
        "body": json.dumps(response_data)
    }

def wait_for_database(cluster_arn, secret_arn, database_name, timeout_limit, start_time):
    """Wait for database to become available by testing connectivity"""
    logger.info("Testing database connectivity...")
    logger.info(f"Using cluster ARN: {cluster_arn}")
    logger.info(f"Using secret ARN: {secret_arn}")
    logger.info(f"Using database name: {database_name}")
    
    max_db_wait_attempts = 20  # Increased from 10 to 20
    for attempt in range(max_db_wait_attempts):
        try:
            # Check if we're about to time out
            if time.time() - start_time > timeout_limit:
                logger.warning("Approaching Lambda timeout during database availability check")
                return False
                
            # Simple query to test connectivity
            logger.info(f"Attempting to execute SQL statement (attempt {attempt+1}/{max_db_wait_attempts})...")
            response = rds_client.execute_statement(
                resourceArn=cluster_arn,
                secretArn=secret_arn,
                database=database_name,
                sql="SELECT current_timestamp"
            )
            
            logger.info(f"Database connectivity test succeeded on attempt {attempt+1}/{max_db_wait_attempts}")
            logger.info(f"Response: {response}")
            return True
            
        except Exception as e:
            error_message = str(e)
            wait_time = min(5 * (attempt + 1), 20)  # Reduced wait times: 5, 10, 15, 20, 20...
            
            # Calculate remaining time
            remaining_time = timeout_limit - (time.time() - start_time)
            if wait_time + 10 > remaining_time:
                logger.warning(f"Not enough time for next database connectivity wait cycle")
                return False
            
            logger.warning(f"Database not yet available (attempt {attempt+1}/{max_db_wait_attempts}). Error: {error_message}")
            
            if "communications link failure" in error_message.lower() or "network" in error_message.lower():
                logger.warning("Network connectivity issue detected")
            elif "access denied" in error_message.lower() or "permission" in error_message.lower():
                logger.warning("Permissions/authentication issue detected")
            elif "does not exist" in error_message.lower():
                logger.warning("Database does not exist yet or is not ready")
            
            logger.info(f"Waiting {wait_time} seconds before next connectivity test...")
            time.sleep(wait_time)
    
    logger.error(f"Database connectivity test failed after {max_db_wait_attempts} attempts")
    return False

def init_database(cluster_arn, secret_arn, database_name, table_name, context):
    """Initialize the database with the pgvector extension and required tables"""
    
    # Calculate timeout limit with 30-second buffer
    timeout_limit = context.get_remaining_time_in_millis() / 1000 - 30
    start_time = time.time()
    
    # Initial wait to allow the database to be available
    logger.info("Waiting for database to be fully available...")
    time.sleep(20)  # Initial wait before connectivity testing
    
    # Test database connectivity with retries
    if not wait_for_database(cluster_arn, secret_arn, database_name, timeout_limit, start_time):
        logger.warning("Could not establish reliable database connectivity. Lambda will exit and CloudFormation will retry.")
        return False
        
    logger.info("Database connectivity confirmed, proceeding with initialization")
    
    # SQL commands to execute
    sql_commands = [
        # Enable pgvector extension
        f"CREATE EXTENSION IF NOT EXISTS vector",
        
        # Create the table with vector column
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            chunk_id VARCHAR(36) PRIMARY KEY,
            workspace_id VARCHAR(100) NOT NULL,
            document_id VARCHAR(100) NOT NULL,
            document_sub_id VARCHAR(100),
            document_type VARCHAR(50),
            document_sub_type VARCHAR(50),
            path VARCHAR(1000),
            title VARCHAR(500),
            content TEXT,
            content_embeddings vector(1536),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Create indices
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_workspace_id ON {table_name} (workspace_id)",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_document_id ON {table_name} (document_id)",
        
        # Create vector index for similarity search
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_vector ON {table_name} USING ivfflat (content_embeddings vector_l2_ops) WITH (lists = 100)"
    ]
    
    # Execute each SQL command with timeout awareness
    executed_commands = []
    max_attempts = 3
    
    for sql in sql_commands:
        attempts = 0
        success = False
        
        while attempts < max_attempts and not success:
            attempts += 1
            try:
                # Check if we're about to time out
                if time.time() - start_time > timeout_limit:
                    logger.warning(f"Approaching Lambda timeout. Successfully executed commands: {executed_commands}")
                    # We return without raising an exception - CloudFormation will retry the custom resource
                    return False
                
                logger.info(f"Executing SQL (attempt {attempts}/{max_attempts}): {sql}")
                
                response = rds_client.execute_statement(
                    resourceArn=cluster_arn,
                    secretArn=secret_arn,
                    database=database_name,
                    sql=sql
                )
                
                logger.info(f"SQL execution result: {response}")
                executed_commands.append(sql.split()[0:3])  # Just log first few words for brevity
                success = True
            
            except Exception as e:
                error_message = str(e)
                logger.warning(f"SQL execution error (attempt {attempts}/{max_attempts}): {error_message}")
                
                # If this is the last attempt, raise the exception
                if attempts >= max_attempts:
                    logger.error(f"All {max_attempts} attempts failed for SQL: {sql}")
                    raise
                
                # Calculate backoff time - exponential but capped by timeout
                backoff_time = min(5 * (2 ** (attempts - 1)), 30)  # 5, 10, 20, 30, 30...
                remaining_time = timeout_limit - (time.time() - start_time)
                
                # Don't sleep longer than our remaining time with buffer
                if backoff_time + 10 > remaining_time:
                    logger.warning(f"Not enough time for backoff, approaching Lambda timeout")
                    # Return without raising exception so CloudFormation will retry
                    return False
                
                logger.info(f"Backing off for {backoff_time} seconds before retry")
                time.sleep(backoff_time)
    
    logger.info(f"Successfully initialized database with vector extension and {table_name} table")
    return True
