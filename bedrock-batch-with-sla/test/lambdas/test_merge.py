import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/merge'))

os.environ.setdefault('OUTPUT_BUCKET_NAME', 'test-output-bucket')
import index


def make_paginator(pages):
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = iter(pages)
    return mock_paginator


def make_body(content):
    if isinstance(content, (dict, list)):
        content = json.dumps(content)
    return {'Body': MagicMock(read=lambda: content.encode())}


def make_event(job_id='job-001'):
    return {
        'jobId': job_id,
        'outputUri': f's3://test-output-bucket/batch-output/{job_id}/',
        'reconcileResult': {'unprocessedCount': 0, 'processedCount': 0, 'unprocessedKey': ''},
    }


class TestMergeOnDemandOnly(unittest.TestCase):
    """Fallback path: all records redriven on-demand, no batch output."""

    def setUp(self):
        os.environ['OUTPUT_BUCKET_NAME'] = 'test-output-bucket'

    @patch('index.s3')
    def test_merge_ondemand_results(self, mock_s3):
        """Parses ResultWriter envelope and extracts recordId + body."""
        executions = [
            {
                'Status': 'SUCCEEDED',
                'Output': json.dumps({
                    'modelOutput': {
                        'recordId': 'r1',
                        'body': {'content': [{'text': 'Paris'}]}
                    }
                })
            },
            {
                'Status': 'SUCCEEDED',
                'Output': json.dumps({
                    'modelOutput': {
                        'recordId': 'r2',
                        'body': {'content': [{'text': 'Berlin'}]}
                    }
                })
            },
        ]

        # batch paginator returns nothing; ondemand paginator returns the executions file
        batch_paginator = make_paginator([{'Contents': []}])
        ondemand_paginator = make_paginator([
            {'Contents': [{'Key': 'ondemand-results/job-001/run/SUCCEEDED_0.json'}]}
        ])
        mock_s3.get_paginator.side_effect = [batch_paginator, ondemand_paginator]
        mock_s3.get_object.return_value = make_body(executions)
        mock_s3.put_object.return_value = {}

        result = index.handler(make_event(), None)

        self.assertEqual(result['totalRecords'], 2)
        self.assertEqual(result['ondemandRecords'], 2)
        self.assertEqual(result['batchRecords'], 0)

        written = mock_s3.put_object.call_args[1]['Body'].decode()
        lines = [json.loads(l) for l in written.strip().split('\n')]
        record_ids = {l['recordId'] for l in lines}
        self.assertEqual(record_ids, {'r1', 'r2'})

    @patch('index.s3')
    def test_failed_executions_excluded(self, mock_s3):
        """Child executions with Status != SUCCEEDED are not included in output."""
        executions = [
            {
                'Status': 'SUCCEEDED',
                'Output': json.dumps({'modelOutput': {'recordId': 'r1', 'body': {}}})
            },
            {
                'Status': 'FAILED',
                'Output': json.dumps({'error': 'something went wrong'})
            },
        ]
        mock_s3.get_paginator.side_effect = [
            make_paginator([{'Contents': []}]),
            make_paginator([{'Contents': [{'Key': 'ondemand-results/job-001/SUCCEEDED_0.json'}]}]),
        ]
        mock_s3.get_object.return_value = make_body(executions)
        mock_s3.put_object.return_value = {}

        result = index.handler(make_event(), None)

        self.assertEqual(result['ondemandRecords'], 1)

    @patch('index.s3')
    def test_manifest_json_skipped(self, mock_s3):
        """manifest.json files in ondemand-results are not parsed as execution output."""
        mock_s3.get_paginator.side_effect = [
            make_paginator([{'Contents': []}]),
            make_paginator([{'Contents': [
                {'Key': 'ondemand-results/job-001/manifest.json'},
            ]}]),
        ]
        mock_s3.put_object.return_value = {}

        result = index.handler(make_event(), None)

        self.assertEqual(result['ondemandRecords'], 0)
        mock_s3.get_object.assert_not_called()


class TestMergeBatchAndOnDemand(unittest.TestCase):
    """Happy-path partial fallback: some batch, some on-demand."""

    def setUp(self):
        os.environ['OUTPUT_BUCKET_NAME'] = 'test-output-bucket'

    @patch('index.s3')
    def test_ondemand_takes_precedence_for_duplicates(self, mock_s3):
        """If a recordId appears in both batch and on-demand, on-demand wins."""
        batch_record = {'recordId': 'r1', 'modelOutput': {'content': 'batch-version'}}
        ondemand_execution = [{
            'Status': 'SUCCEEDED',
            'Output': json.dumps({'modelOutput': {'recordId': 'r1', 'body': {'content': 'ondemand-version'}}})
        }]

        mock_s3.get_paginator.side_effect = [
            make_paginator([{'Contents': [{'Key': 'batch-output/job-001/output.jsonl.out'}]}]),
            make_paginator([{'Contents': [{'Key': 'ondemand-results/job-001/SUCCEEDED_0.json'}]}]),
        ]
        mock_s3.get_object.side_effect = [
            make_body(json.dumps(batch_record)),
            make_body(ondemand_execution),
        ]
        mock_s3.put_object.return_value = {}

        result = index.handler(make_event(), None)

        self.assertEqual(result['totalRecords'], 1)
        written = mock_s3.put_object.call_args[1]['Body'].decode()
        record = json.loads(written.strip())
        # on-demand result stored as {recordId, modelOutput: body}
        self.assertEqual(record['modelOutput']['content'], 'ondemand-version')

    @patch('index.s3')
    def test_always_writes_output_file(self, mock_s3):
        """Output file is written even when merged_results is empty."""
        mock_s3.get_paginator.side_effect = [
            make_paginator([{'Contents': []}]),
            make_paginator([{'Contents': []}]),
        ]
        mock_s3.put_object.return_value = {}

        result = index.handler(make_event(), None)

        mock_s3.put_object.assert_called_once()
        self.assertEqual(result['totalRecords'], 0)

    @patch('index.s3')
    def test_pagination_used_for_both_listings(self, mock_s3):
        """Both batch and ondemand listings use get_paginator, not list_objects_v2."""
        mock_s3.get_paginator.side_effect = [
            make_paginator([{'Contents': []}]),
            make_paginator([{'Contents': []}]),
        ]
        mock_s3.put_object.return_value = {}

        index.handler(make_event(), None)

        self.assertEqual(mock_s3.get_paginator.call_count, 2)
        mock_s3.list_objects_v2.assert_not_called()


if __name__ == '__main__':
    unittest.main()
