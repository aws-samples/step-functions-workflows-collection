import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add lambdas directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/store-token'))

import index

class TestStoreTokenLambda(unittest.TestCase):

    def setUp(self):
        os.environ['JOBS_TABLE_NAME'] = 'test-jobs-table'
        os.environ['MODEL_ID'] = 'test-model-id'

    @patch('index.dynamodb')
    def test_store_token_success(self, mock_dynamodb):
        """Test successful token storage"""
        event = {
            'jobId': 'test-job-123',
            'bedrockJobArn': 'arn:aws:bedrock:us-east-1:123456789012:model-invocation-job/test-job',
            'taskToken': 'test-token-abc123'
        }

        mock_dynamodb.update_item.return_value = {}

        result = index.handler(event, None)

        self.assertEqual(result['statusCode'], 200)
        self.assertIn('success', result['message'].lower())

        # Verify DynamoDB was called with correct parameters
        mock_dynamodb.update_item.assert_called_once()
        call_args = mock_dynamodb.update_item.call_args[1]
        self.assertEqual(call_args['TableName'], 'test-jobs-table')
        self.assertEqual(call_args['Key']['JobId']['S'], 'test-job-123')

        # Verify update expression contains required fields
        self.assertIn('TaskToken', call_args['UpdateExpression'])
        self.assertIn('BedrockJobArn', call_args['UpdateExpression'])
        self.assertIn('#status', call_args['UpdateExpression'])

        # Verify attribute values
        self.assertEqual(
            call_args['ExpressionAttributeValues'][':token']['S'],
            'test-token-abc123'
        )
        self.assertEqual(
            call_args['ExpressionAttributeValues'][':arn']['S'],
            'arn:aws:bedrock:us-east-1:123456789012:model-invocation-job/test-job'
        )
        self.assertEqual(
            call_args['ExpressionAttributeValues'][':status']['S'],
            'InProgress'
        )

    @patch('index.dynamodb')
    def test_store_token_missing_field(self, mock_dynamodb):
        """Test error handling when required field is missing"""
        event = {
            'jobId': 'test-job-123',
            # Missing bedrockJobArn and taskToken
        }

        with self.assertRaises(KeyError):
            index.handler(event, None)

        # DynamoDB should not be called if validation fails
        mock_dynamodb.update_item.assert_not_called()

    @patch('index.dynamodb')
    def test_store_token_dynamodb_error(self, mock_dynamodb):
        """Test error handling when DynamoDB fails"""
        event = {
            'jobId': 'test-job-123',
            'bedrockJobArn': 'arn:aws:bedrock:us-east-1:123456789012:model-invocation-job/test-job',
            'taskToken': 'test-token-abc123'
        }

        mock_dynamodb.update_item.side_effect = Exception('DynamoDB error')

        with self.assertRaises(Exception) as context:
            index.handler(event, None)

        self.assertIn('DynamoDB error', str(context.exception))


if __name__ == '__main__':
    unittest.main()
