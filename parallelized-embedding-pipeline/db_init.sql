-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the table with vector column
CREATE TABLE IF NOT EXISTS vectortable (
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
);

-- Create indices
CREATE INDEX IF NOT EXISTS idx_vectortable_workspace_id ON vectortable (workspace_id);
CREATE INDEX IF NOT EXISTS idx_vectortable_document_id ON vectortable (document_id);

-- Create vector index for similarity search
CREATE INDEX IF NOT EXISTS idx_vectortable_vector ON vectortable USING ivfflat (content_embeddings vector_l2_ops) WITH (lists = 100);
