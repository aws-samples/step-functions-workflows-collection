"""
Shared boto3 client configuration for Lambda functions.

Provides retry and timeout settings following AWS best practices.
"""
from botocore.config import Config

# Standard retry configuration with exponential backoff
# - max_attempts: 3 retries (4 total attempts)
# - mode: adaptive (adjusts based on service throttling signals)
RETRY_CONFIG = Config(
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'
    },
    connect_timeout=5,  # 5 seconds to establish connection
    read_timeout=60,    # 60 seconds to read response
)

# Longer timeout for operations that may take more time (e.g., Bedrock API)
EXTENDED_TIMEOUT_CONFIG = Config(
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'
    },
    connect_timeout=5,
    read_timeout=120,  # 2 minutes for slower APIs
)
