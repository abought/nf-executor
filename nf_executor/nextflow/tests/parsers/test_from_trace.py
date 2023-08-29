"""Test the ability to parse trace file contents"""
import os
from unittest import TestCase

from nf_executor.api.enums import TaskStatus
from nf_executor.nextflow.parsers import from_trace

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '../fixtures')


def get_trace_contents() -> str:
    """Get a trace file that has been dummied with both completion AND failure records"""
    fn = os.path.join(FIXTURE_DIR, 'nextflow-mock-full-trace.txt')
    with open(fn, 'r') as f:
        return f.read()


class TestFromTrace(TestCase):
    def setUp(self) -> None:
        self.content: str = get_trace_contents()

    def test_parser_reads_log(self):
        items = from_trace.parse_tracelog(self.content)
        self.assertTrue(
            all(isinstance(item, from_trace.NFTraceEvent) for item in items),
            'Returns Trace items'
        )
        self.assertEqual(len(items), 7, 'Parses one record per line')

    def test_helper_consolidates_items(self):
        items = from_trace.parse_tracelog(self.content)
        items = items.consolidate()
        self.assertEqual(len(items), 4, 'Parses consolidates items')
        self.assertListEqual(
            [item.task_id for item in items],
            [ '1', '2', '3', '4'],
            'Consolidator returns one item per task reported'
        )

        self.assertListEqual(
            [item.status for item in items],
            [TaskStatus.COMPLETED, TaskStatus.COMPLETED, TaskStatus.COMPLETED, TaskStatus.FAILED],
            'Consolidation chooses the highest status for all tasks'
        )

    def test_helper_checks_abort(self):
        items = from_trace.parse_tracelog(self.content)
        del items[-2]  # Remove the "failed" record for last task, so that the list consolidates to "aborted"
        self.assertTrue(items.any_aborted(), 'Detects aborted items in record collection')

    def test_helper_checks_failed(self):
        items = from_trace.parse_tracelog(self.content)
        self.assertTrue(items.any_failed(), 'Detects failed items in record collection')

    def test_helper_checks_all_complete(self):
        items = from_trace.parse_tracelog(self.content)[:3]  # Remove task 4 (the failed item) from sample dataset
        self.assertTrue(items.all_complete(), 'Verifies all items in record collection were completed')

