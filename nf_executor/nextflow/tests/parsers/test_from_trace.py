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
        self.content = get_trace_contents()

    def test_parser_reads_log(self):
        items = from_trace.parse_tracelog(self.content)
        self.assertTrue(
            all(isinstance(item, from_trace.NFTraceEvent) for item in items),
            'Returns Trace items'
        )
        self.assertEqual(len(items), 7, 'Parses one record per line')

    def test_parser_consolidates_items(self):
        items = from_trace.parse_tracelog(self.content, consolidate=True)
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

