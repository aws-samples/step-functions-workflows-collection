import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/registrar'))

import index

class TestRegistrarLambda(unittest.TestCase):

    def setUp(self):
        os.environ['JOBS_TABLE_NAME'] = 'test-jobs-table'
        os.environ['STATE_MACHINE_ARN'] = 'arn:aws:states:us-east-1:123456789012:stateMachine:test-machine'
        os.environ['OUTPUT_BUCKET_NAME'] = 'test-output-bucket'
        os.environ['MODEL_ID'] = 'test-model-id'

    @patch('index.sfn')
    @patch('index.dynamodb')
    @patch('index.uuid')
    def test_registrar_success(self, mock_uuid, mock_dynamodb, mock_sfn):
        """Test successful job registration and execution start"""
        mock_uuid.uuid4.return_value = 'test-job-uuid'

        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': 'test-input-bucket'},
                    'object': {'key': 'path/to/input.jsonl'}
                }
            }]
        }

        mock_dynamodb.put_item.return_value = {}
        mock_sfn.start_execution.return_value = {
            'executionArn': 'arn:aws:states:us-east-1:123456789012:execution:test-machine:test-execution'
        }

        result = index.handler(event, None)

        self.assertEqual(result['statusCode'], 200)
        body = json.loads(result['body'])
        self.assertEqual(body['jobId'], 'test-job-uuid')

        # Verify DynamoDB put_item was called
        mock_dynamodb.put_item.assert_called_once()
        dynamo_call = mock_dynamodb.put_item.call_args[1]
        self.assertEqual(dynamo_call['TableName'], 'test-jobs-table')
        self.assertEqual(dynamo_call['Item']['JobId']['S'], 'test-job-uuid')
        self.assertEqual(dynamo_call['Item']['Status']['S'], 'Pending')
        self.assertEqual(
            dynamo_call['Item']['S3InputLocation']['S'],
            's3://test-input-bucket/path/to/input.jsonl'
        )

        # Verify Step Functions start_execution was called
        mock_sfn.start_execution.assert_called_once()
        sfn_call = mock_sfn.start_execution.call_args[1]
        self.assertEqual(
            sfn_call['stateMachineArn'],
            'arn:aws:states:us-east-1:123456789012:stateMachine:test-machine'
        )
        execution_input = json.loads(sfn_call['input'])
        self.assertEqual(execution_input['jobId'], 'test-job-uuid')

    @patch('index.dynamodb')
    def test_registrar_missing_s3_record(self, mock_dynamodb):
        """Test error handling when S3 event is malformed"""
        event = {'Records': []}

        with self.assertRaises(Exception):
            index.handler(event, None)


if __name__ == '__main__':
    unittest.main()
