import math, os

def lambda_handler(event, context):
    # Extract parameters from the event
    object_size = event.get('objectSize', 0)
    chunk_size = int(os.environ.get('CHUNK_SIZE', '1024'))
    chunk_overlap = int(os.environ.get('CHUNK_OVERLAP', '0'))
    
    # Print the parameters for debugging
    print(f"Processing object with size: {object_size} bytes, chunk size: {chunk_size}, overlap: {chunk_overlap}")
    
    # Handle edge cases:
    # 1. Empty object or invalid size (shouldn't happen, but just in case)
    if object_size <= 0:
        print("Warning: Object size is zero or negative, returning empty byte ranges")
        return {
            'statusCode': 200,
            'body': 'Object has zero size - no byte ranges to process',
            'byteRanges': []
        }
    
    # 2. Small object - process it as a single chunk regardless of chunk size
    if object_size <= chunk_size:
        print(f"Object size {object_size} is smaller than chunk size {chunk_size}, processing as a single chunk")
        byte_ranges = [{
            'start': 0,
            'end': object_size - 1
        }]
    else:
        # Normal case - calculate multiple chunks
        effective_chunk_size = chunk_size - chunk_overlap
        # Ensure we don't get a negative divisor
        if effective_chunk_size <= 0:
            effective_chunk_size = chunk_size
            chunk_overlap = 0
            
        # Calculate the number of chunks with proper handling of edge cases
        num_chunks = max(1, math.ceil((object_size - chunk_overlap) / effective_chunk_size))
        print(f"Calculated {num_chunks} chunks for processing")
        
        # Generate the byte ranges
        byte_ranges = []
        for i in range(num_chunks):
            start = i * effective_chunk_size
            end = min(start + chunk_size - 1, object_size - 1)
            byte_ranges.append({
                'start': start,
                'end': end
            })
        
        # Adjust the last byte range to include any remaining bytes
        if byte_ranges:
            byte_ranges[-1]['end'] = object_size - 1

    # Return the byte ranges
    return {
        'statusCode': 200,
        'body': 'Byte ranges generated successfully',
        'byteRanges': byte_ranges
    }
