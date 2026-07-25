import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/resume'))

os.environ.setdefault('JOBS_TABLE_NAME', 'test-jobs-table')
import index


def make_event(status='Completed', job_arn='arn:aws:bedrock:us-east-1:123:model-invocation-job/job-1'):
    return {
        'detail': {
            'batchJobArn': job_arn,
            'status': status,
        }
    }


def make_dynamo_item(job_id='job-001', task_token='token-abc'):
    return {
        'Items': [{
            'JobId': {'S': job_id},
            'TaskToken': {'S': task_token},
            'BedrockJobArn': {'S': 'arn:aws:bedrock:us-east-1:123:model-invocation-job/job-1'},
        }]
    }


class TestResume(unittest.TestCase):

    def setUp(self):
        os.environ['JOBS_TABLE_NAME'] = 'test-jobs-table'

    @patch('index.sfn')
    @patch('index.dynamodb')
    def test_completed_sends_task_success(self, mock_ddb, mock_sfn):
        """Completed status resumes state machine via send_task_success."""
        mock_ddb.query.return_value = make_dynamo_item()
        mock_ddb.update_item.return_value = {}
        mock_sfn.send_task_success.return_value = {}

        result = index.handler(make_event(status='Completed'), None)

        self.assertEqual(result['statusCode'], 200)
        mock_sfn.send_task_success.assert_called_once()
        output = json.loads(mock_sfn.send_task_success.call_args[1]['output'])
        self.assertEqual(output['status'], 'Completed')

    @patch('index.sfn')
    @patch('index.dynamodb')
    def test_failed_sends_task_success_with_failed_status(self, mock_ddb, mock_sfn):
        """Failed status also uses send_task_success — CheckOutcome routes to fallback."""
        mock_ddb.query.return_value = make_dynamo_item()
        mock_ddb.update_item.return_value = {}
        mock_sfn.send_task_success.return_value = {}

        result = index.handler(make_event(status='Failed'), None)

        self.assertEqual(result['statusCode'], 200)
        output = json.loads(mock_sfn.send_task_success.call_args[1]['output'])
        self.assertEqual(output['status'], 'Failed')

    @patch('index.sfn')
    @patch('index.dynamodb')
    def test_partially_completed_sends_task_success(self, mock_ddb, mock_sfn):
        """PartiallyCompleted routes to fallback via CheckOutcome."""
        mock_ddb.query.return_value = make_dynamo_item()
        mock_ddb.update_item.return_value = {}
        mock_sfn.send_task_success.return_value = {}

        result = index.handler(make_event(status='PartiallyCompleted'), None)

        self.assertEqual(result['statusCode'], 200)
        output = json.loads(mock_sfn.send_task_success.call_args[1]['output'])
        self.assertEqual(output['status'], 'PartiallyCompleted')

    @patch('index.sfn')
    @patch('index.dynamodb')
    def test_job_not_found_returns_404(self, mock_ddb, mock_sfn):
        """Returns 404 when no DynamoDB record matches the job ARN."""
        mock_ddb.query.return_value = {'Items': []}

        result = index.handler(make_event(), None)

        self.assertEqual(result['statusCode'], 404)
        mock_sfn.send_task_success.assert_not_called()

    @patch('index.sfn')
    @patch('index.dynamodb')
    def test_dynamodb_updated_with_status(self, mock_ddb, mock_sfn):
        """Job status is updated in DynamoDB before resuming state machine."""
        mock_ddb.query.return_value = make_dynamo_item()
        mock_ddb.update_item.return_value = {}
        mock_sfn.send_task_success.return_value = {}

        index.handler(make_event(status='Expired'), None)

        update_args = mock_ddb.update_item.call_args[1]
        self.assertIn(':status', update_args['ExpressionAttributeValues'])
        self.assertEqual(update_args['ExpressionAttributeValues'][':status']['S'], 'Expired')

    @patch('index.sfn')
    @patch('index.dynamodb')
    def test_send_task_success_called_exactly_once(self, mock_ddb, mock_sfn):
        """Collapsed if/else — send_task_success is called exactly once regardless of status."""
        mock_ddb.query.return_value = make_dynamo_item()
        mock_ddb.update_item.return_value = {}
        mock_sfn.send_task_success.return_value = {}

        for status in ['Completed', 'Failed', 'Expired', 'PartiallyCompleted']:
            mock_sfn.reset_mock()
            index.handler(make_event(status=status), None)
            self.assertEqual(mock_sfn.send_task_success.call_count, 1,
                             f"Expected exactly 1 send_task_success call for status={status}")


if __name__ == '__main__':
    unittest.main()
