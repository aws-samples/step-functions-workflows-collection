from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, NotFoundError
import boto3
import time
import json

def create_opensearch_client(host, region='us-east-1'):
    """Create OpenSearch client with AWS authentication"""
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, 'aoss')
    
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )
    return client

def delete_existing_indices(client):
    """Delete all existing indices in the collection"""
    try:
        # List all indices
        indices = client.indices.get('*')
        
        # Delete each index
        for index_name in indices:
            print(f"Deleting index: {index_name}")
            client.indices.delete(index=index_name)
            print(f"Successfully deleted index: {index_name}")
            
    except NotFoundError:
        print("No existing indices found")
    except Exception as e:
        print(f"Error deleting indices: {str(e)}")

def create_vector_index(client, index_name, vector_dimension=1024):
    """Create a new vector search index"""
    index_body = {
        "settings": {
            "index.knn": True,
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "vector_field": {
                    "type": "knn_vector",
                    "dimension": vector_dimension,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "space_type": "l2",
                        "parameters": {
                            "ef_construction": 128,
                            "m": 16
                        }
                    }
                },
                "text": {
                    "type": "text"
                },
                "metadata": {
                    "type": "text"
                }
            }
        }
    }

    try:
        response = client.indices.create(
            index=index_name,
            body=json.dumps(index_body)
        )
        print(f"Successfully created index: {index_name}")
        return response
    except Exception as e:
        print(f"Error creating index {index_name}: {str(e)}")
        return None

def main():
    # Replace with your OpenSearch Serverless collection endpoint (without https://)
    host = "<TEST>.<REGION>.aoss.amazonaws.com"
    region = "REGION"  # e.g., us-east-1
    
    # Create OpenSearch client
    client = create_opensearch_client(host, region)
    
    # Delete existing indices
    print("Deleting existing indices...")
    delete_existing_indices(client)
    
    # Wait a bit for deletions to complete
    time.sleep(10)
    
    # Create two new vector indices
    print("\nCreating new indices...")
    
    # First index for document embeddings
    create_vector_index(
        client,
        "vector-index-1",
        vector_dimension=1024  # Adjust dimension based on your embedding model
    )
    
    # Second index for image embeddings
    create_vector_index(
        client,
        "vector-index-2",
        vector_dimension=1024  # Adjust dimension based on your embedding model
    )
    
    # Wait for indices to be ready
    time.sleep(30)
    
    # Verify indices were created
    try:
        indices = client.indices.get('*')
        print("\nCreated indices:")
        for index_name in indices:
            print(f"- {index_name}")
    except Exception as e:
        print(f"Error verifying indices: {str(e)}")

if __name__ == "__main__":
    main()
