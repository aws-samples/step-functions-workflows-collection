import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/trigger'))

os.environ.setdefault('JOBS_TABLE_NAME', 'test-jobs-table')
os.environ.setdefault('MODEL_ID', 'test-model')
import index


def make_sns_event(alarm_name='bedrock-batch-sla-stuck-job'):
    return {
        'Records': [{
            'Sns': {
                'Message': json.dumps({'AlarmName': alarm_name})
            }
        }]
    }


def make_dynamo_item(job_id='job-001', task_token='token-xyz', bedrock_arn='arn:aws:bedrock:us-east-1:123:model-invocation-job/job-1'):
    return {
        'Items': [{
            'JobId': {'S': job_id},
            'TaskToken': {'S': task_token},
            'BedrockJobArn': {'S': bedrock_arn},
            'Status': {'S': 'InProgress'},
        }]
    }


class TestTrigger(unittest.TestCase):

    def setUp(self):
        os.environ['JOBS_TABLE_NAME'] = 'test-jobs-table'
        os.environ['MODEL_ID'] = 'us.anthropic.claude-sonnet-4-6'

    @patch('index.sfn')
    @patch('index.bedrock')
    @patch('index.dynamodb')
    def test_stuck_inprogress_job_triggers_fallback(self, mock_ddb, mock_bedrock, mock_sfn):
        """InProgress job triggers fallback with FallbackRequested status."""
        mock_ddb.query.return_value = make_dynamo_item()
        mock_ddb.update_item.return_value = {}
        mock_bedrock.get_model_invocation_job.return_value = {
            'status': 'InProgress',
            'inputDataConfig': {'recordCount': 1000},
            'outputDataConfig': {'recordCount': 100},
        }
        mock_sfn.send_task_success.return_value = {}

        result = index.handler(make_sns_event(), None)

        self.assertEqual(result['statusCode'], 200)
        mock_sfn.send_task_success.assert_called_once()
        output = json.loads(mock_sfn.send_task_success.call_args[1]['output'])
        self.assertEqual(output['status'], 'FallbackRequested')
        self.assertEqual(output['reason'], 'stuck_or_slow')

    @patch('index.sfn')
    @patch('index.bedrock')
    @patch('index.dynamodb')
    def test_validating_job_triggers_fallback(self, mock_ddb, mock_bedrock, mock_sfn):
        """Validating job (early stuck state) also triggers fallback."""
        mock_ddb.query.return_value = make_dynamo_item()
        mock_ddb.update_item.return_value = {}
        mock_bedrock.get_model_invocation_job.return_value = {'status': 'Validating'}
        mock_sfn.send_task_success.return_value = {}

        result = index.handler(make_sns_event(), None)

        self.assertEqual(result['statusCode'], 200)
        mock_sfn.send_task_success.assert_called_once()

    @patch('index.sfn')
    @patch('index.bedrock')
    @patch('index.dynamodb')
    def test_no_active_jobs_returns_200(self, mock_ddb, mock_bedrock, mock_sfn):
        """No InProgress jobs — returns 200, no fallback triggered."""
        mock_ddb.query.return_value = {'Items': []}

        result = index.handler(make_sns_event(), None)

        self.assertEqual(result['statusCode'], 200)
        mock_sfn.send_task_success.assert_not_called()

    @patch('index.sfn')
    @patch('index.bedrock')
    @patch('index.dynamodb')
    def test_bedrock_error_continues_to_next_job(self, mock_ddb, mock_bedrock, mock_sfn):
        """If Bedrock call fails for one job, loop continues to the next."""
        items = [
            {'JobId': {'S': 'job-fail'}, 'TaskToken': {'S': 'tok1'}, 'BedrockJobArn': {'S': 'arn:1'}},
            {'JobId': {'S': 'job-ok'}, 'TaskToken': {'S': 'tok2'}, 'BedrockJobArn': {'S': 'arn:2'}},
        ]
        mock_ddb.query.return_value = {'Items': items}
        mock_ddb.update_item.return_value = {}
        mock_bedrock.get_model_invocation_job.side_effect = [
            Exception('Bedrock API error'),
            {'status': 'InProgress'},
        ]
        mock_sfn.send_task_success.return_value = {}

        result = index.handler(make_sns_event(), None)

        self.assertEqual(result['statusCode'], 200)
        mock_sfn.send_task_success.assert_called_once()
        self.assertEqual(mock_sfn.send_task_success.call_args[1]['taskToken'], 'tok2')

    @patch('index.sfn')
    @patch('index.bedrock')
    @patch('index.dynamodb')
    def test_queries_status_index(self, mock_ddb, mock_bedrock, mock_sfn):
        """DynamoDB query uses StatusIndex to find InProgress jobs."""
        mock_ddb.query.return_value = {'Items': []}

        index.handler(make_sns_event(), None)

        query_args = mock_ddb.query.call_args[1]
        self.assertEqual(query_args['IndexName'], 'StatusIndex')
        self.assertIn(':status', query_args['ExpressionAttributeValues'])
        self.assertEqual(query_args['ExpressionAttributeValues'][':status']['S'], 'InProgress')


if __name__ == '__main__':
    unittest.main()
