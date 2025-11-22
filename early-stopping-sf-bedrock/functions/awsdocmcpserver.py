import json
import subprocess
import sys
import os
# import tempfile
import asyncio
import shutil
import glob


# Initialize MCP server at module level (runs once per container)
print("Initializing MCP server...")

# Install packages to persistent location
temp_dir = "/tmp/mcp_packages"
os.makedirs(temp_dir, exist_ok=True)

# Only install if not already installed
if not os.path.exists(os.path.join(temp_dir, "awslabs")):
    print(f"Installing packages to {temp_dir}")
    
    # Clear any existing SSL environment variables
    ssl_env_vars = ["SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"]
    for var in ssl_env_vars:
        if var in os.environ:
            del os.environ[var]
    
    # Install packages
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", 
        "awslabs.aws-documentation-mcp-server", 
        "certifi", 
        "--target", temp_dir,
        "--trusted-host", "pypi.org",
        "--trusted-host", "pypi.python.org", 
        "--trusted-host", "files.pythonhosted.org"
    ])

# Add to path
sys.path.insert(0, temp_dir)

# Set environment variables
os.environ["FASTMCP_LOG_LEVEL"] = "ERROR"
os.environ["AWS_DOCUMENTATION_PARTITION"] = "AWS"

# Find and set SSL certificates
cert_pattern = os.path.join(temp_dir, "**/cacert.pem")
cert_files = glob.glob(cert_pattern, recursive=True)

if not cert_files:
    # Fallback: try to find any .pem file
    pem_pattern = os.path.join(temp_dir, "**/*.pem")
    cert_files = glob.glob(pem_pattern, recursive=True)

if cert_files:
    # Use the first certificate file found
    cert_path = cert_files[0]
    print(f"Found certificate file: {cert_path}")
    
    # Copy to persistent location
    persistent_cert_path = "/tmp/cacert.pem"
    shutil.copy2(cert_path, persistent_cert_path)
    
    # Set SSL environment variables
    os.environ["SSL_CERT_FILE"] = persistent_cert_path
    os.environ["REQUESTS_CA_BUNDLE"] = persistent_cert_path
    os.environ["CURL_CA_BUNDLE"] = persistent_cert_path
    print(f"SSL certificates set to: {persistent_cert_path}")
else:
    print("Warning: No certificate file found")

print("MCP server initialization complete")

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, 'dict'):
            return obj.dict()
        return super().default(obj)

async def async_handler(event, context):
    try:
        # Process the request
        action = event.get('action')
        
        if action == 'search':
            search_phrase = event.get('search_phrase', '')
            limit = event.get('limit', 5)
            
            print(f"Searching for: {search_phrase}")
            
            # Import and use MCP server
            from awslabs.aws_documentation_mcp_server import server_aws
            
            class MockContext:
                pass
            
            mock_ctx = MockContext()
            result = await server_aws.search_documentation(mock_ctx, search_phrase=search_phrase, limit=limit)
            
            # Convert to JSON
            result_json = json.loads(json.dumps(result, cls=CustomJSONEncoder))
            
            print(f"Search completed successfully")
            return {
                "output": {
                    "kind": "text",
                    "content": json.dumps(result_json)
                }
            }
        
        else:
            return {"error": f"Unsupported action: {action}"}
            
    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_msg)
        return {"error": error_msg}

def handler(event, context):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(async_handler(event, context))
            return result
        finally:
            loop.close()
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
