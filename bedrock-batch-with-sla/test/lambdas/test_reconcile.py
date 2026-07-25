import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/reconcile'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas'))

os.environ.setdefault('OUTPUT_BUCKET_NAME', 'test-output-bucket')
import index
from common.s3_utils import parse_s3_uri


def make_paginator(pages):
    """Return a mock paginator that yields the given pages."""
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = iter(pages)
    return mock_paginator


class TestReconcile(unittest.TestCase):

    def setUp(self):
        os.environ['OUTPUT_BUCKET_NAME'] = 'test-output-bucket'

    def _make_event(self, job_id='job-001'):
        return {
            'jobId': job_id,
            'inputUri': 's3://test-input-bucket/input.jsonl',
            'outputUri': f's3://test-output-bucket/batch-output/{job_id}/',
        }

    @patch('index.s3')
    def test_all_records_unprocessed_no_manifest(self, mock_s3):
        """When batch produced no output, all input records are unprocessed."""
        input_records = [
            {'recordId': 'r1', 'modelInput': {}},
            {'recordId': 'r2', 'modelInput': {}},
        ]
        mock_s3.get_object.side_effect = [
            # input.jsonl
            {'Body': MagicMock(read=lambda: ('\n'.join(json.dumps(r) for r in input_records)).encode())},
            # manifest — raises (not found)
            Exception('NoSuchKey'),
        ]
        mock_s3.get_paginator.return_value = make_paginator([{'Contents': []}])
        mock_s3.put_object.return_value = {}

        result = index.handler(self._make_event(), None)

        self.assertEqual(result['unprocessedCount'], 2)
        self.assertEqual(result['processedCount'], 0)
        mock_s3.put_object.assert_called_once()

    @patch('index.s3')
    def test_some_records_processed(self, mock_s3):
        """Records found in batch output are excluded from unprocessed list."""
        input_records = [
            {'recordId': 'r1', 'modelInput': {}},
            {'recordId': 'r2', 'modelInput': {}},
            {'recordId': 'r3', 'modelInput': {}},
        ]
        batch_output = [
            {'recordId': 'r1', 'modelOutput': {'content': 'done'}},
        ]
        manifest = {'successCount': 1, 'errorCount': 0}

        mock_s3.get_object.side_effect = [
            {'Body': MagicMock(read=lambda: ('\n'.join(json.dumps(r) for r in input_records)).encode())},
            {'Body': MagicMock(read=lambda: json.dumps(manifest).encode())},
            {'Body': MagicMock(read=lambda: ('\n'.join(json.dumps(r) for r in batch_output)).encode())},
        ]
        mock_s3.get_paginator.return_value = make_paginator([
            {'Contents': [{'Key': 'batch-output/job-001/output.jsonl.out'}]}
        ])
        mock_s3.put_object.return_value = {}

        result = index.handler(self._make_event(), None)

        self.assertEqual(result['processedCount'], 1)
        self.assertEqual(result['unprocessedCount'], 2)

    @patch('index.s3')
    def test_all_records_processed_no_write(self, mock_s3):
        """When all records are processed no unprocessed file is written."""
        input_records = [{'recordId': 'r1', 'modelInput': {}}]
        batch_output = [{'recordId': 'r1', 'modelOutput': {}}]
        manifest = {'successCount': 1, 'errorCount': 0}

        mock_s3.get_object.side_effect = [
            {'Body': MagicMock(read=lambda: json.dumps(input_records[0]).encode())},
            {'Body': MagicMock(read=lambda: json.dumps(manifest).encode())},
            {'Body': MagicMock(read=lambda: json.dumps(batch_output[0]).encode())},
        ]
        mock_s3.get_paginator.return_value = make_paginator([
            {'Contents': [{'Key': 'batch-output/job-001/output.jsonl.out'}]}
        ])

        result = index.handler(self._make_event(), None)

        self.assertEqual(result['unprocessedCount'], 0)
        mock_s3.put_object.assert_not_called()

    @patch('index.s3')
    def test_pagination_used_for_output_listing(self, mock_s3):
        """list_objects_v2 is called via paginator, not directly."""
        input_records = [{'recordId': 'r1', 'modelInput': {}}]
        manifest = {'successCount': 1, 'errorCount': 0}
        mock_s3.get_object.side_effect = [
            {'Body': MagicMock(read=lambda: json.dumps(input_records[0]).encode())},
            {'Body': MagicMock(read=lambda: json.dumps(manifest).encode())},
        ]
        # paginator returns no .jsonl.out files — simulates empty output dir
        mock_s3.get_paginator.return_value = make_paginator([{'Contents': []}])
        mock_s3.put_object.return_value = {}

        index.handler(self._make_event(), None)

        mock_s3.get_paginator.assert_called_once_with('list_objects_v2')
        mock_s3.list_objects_v2.assert_not_called()


class TestReconcileHelpers(unittest.TestCase):

    def test_parse_s3_uri(self):
        bucket, key = parse_s3_uri('s3://my-bucket/path/to/file.jsonl')
        self.assertEqual(bucket, 'my-bucket')
        self.assertEqual(key, 'path/to/file.jsonl')

    def test_parse_s3_uri_no_key(self):
        bucket, key = parse_s3_uri('s3://my-bucket')
        self.assertEqual(bucket, 'my-bucket')
        self.assertEqual(key, '')


if __name__ == '__main__':
    unittest.main()
