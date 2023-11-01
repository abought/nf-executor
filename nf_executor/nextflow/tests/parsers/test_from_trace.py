"""Test the ability to parse trace file contents"""
import os
from unittest import TestCase

from nf_executor.api.enums import TaskStatus
from nf_executor.nextflow.parsers import from_trace
from nf_executor.nextflow.parsers.from_trace import TraceList, NFTraceEvent

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '../fixtures')


def _get_contents(fn: str) -> TraceList[NFTraceEvent]:
    with open(fn, 'r') as f:
        content = f.read()
    return from_trace.parse_tracelog(content)


def get_trace_contents() -> TraceList[NFTraceEvent]:
    """Get a trace file that has been dummied with both completion AND failure records"""
    fn = os.path.join(FIXTURE_DIR, 'trace_files/nextflow-mock-full-trace.txt')
    return _get_contents(fn)


class TestFromTrace(TestCase):
    """Test a set of general trace file scenarios from a catch-all file with a bit of everything"""
    def setUp(self) -> None:
        self._items = get_trace_contents()

    def test_parser_reads_log(self):
        items = self._items
        self.assertTrue(
            all(isinstance(item, from_trace.NFTraceEvent) for item in self._items),
            'Returns Trace items'
        )
        self.assertEqual(len(items), 7, 'Parses one record per line')

    def test_helper_consolidates_items(self):
        items = self._items
        items = items.consolidate()
        self.assertEqual(len(items), 4, 'Parses consolidates items')
        self.assertListEqual(
            [item.task_id for item in items],
            ['1', '2', '3', '4'],
            'Consolidator returns one item per task reported'
        )

        self.assertListEqual(
            [item.status for item in items],
            [TaskStatus.COMPLETED, TaskStatus.COMPLETED, TaskStatus.COMPLETED, TaskStatus.FAILED],
            'Consolidation chooses the highest status for all tasks'
        )

    def test_helper_checks_abort(self):
        items = self._items
        del items[-2]  # Remove the "failed" record for last task, so that the list consolidates to "aborted"
        self.assertTrue(items.any_aborted(), 'Detects aborted items in record collection')

    def test_helper_checks_failed(self):
        items = self._items
        self.assertTrue(items.any_failed(), 'Detects failed items in record collection')

    def test_helper_checks_all_complete(self):
        items = self._items[:3]  # Remove task 4 (the failed item) from sample dataset
        self.assertTrue(items.all_complete(), 'Verifies all items in record collection were completed')


class TestTraceScenarios(TestCase):
    def test_all_success(self):
        """A trace with only successful tasks resolves as successful"""
        fn = os.path.join(FIXTURE_DIR, 'trace_files/job-success-no-retries.txt')
        items = _get_contents(fn)
        self.assertTrue(items.all_complete(), 'All tasks completed')
        self.assertEqual(items.final_status(), TaskStatus.COMPLETED, 'Final trace status is completed')
        self.assertEqual(len(items.consolidate()), 3, 'Three tasks were run')

    def test_success_after_retries(self):
        """A trace with successful retries resolves as successful"""
        fn = os.path.join(FIXTURE_DIR, 'trace_files/job-success-with-task-retries.txt')
        items = _get_contents(fn)
        self.assertTrue(items.all_complete(), 'All tasks completed')
        self.assertFalse(items.any_failed(), 'Retries that succeeded overrule attempts that failed')
        self.assertEqual(len(items.consolidate()), 3, 'Three tasks were run')
        self.assertEqual(items.final_status(), TaskStatus.COMPLETED, 'Final trace status is completed')

    def test_fail_first_try(self):
        """A trace with one task (failed) is marked as a failed job"""
        fn = os.path.join(FIXTURE_DIR, 'trace_files/job-fail-task1-firsttry.txt')
        items = _get_contents(fn)
        self.assertFalse(items.all_complete(), 'Not all tasks completed')
        self.assertTrue(items.any_failed(), 'Some tasks report failure as the highest state')

        self.assertEqual(items.final_status(), TaskStatus.FAILED, 'Final trace status is FAILED')
        self.assertEqual(len(items.consolidate()), 1, 'One task was run')

    def test_fail_many_retries(self):
        """A trace with one task (that failed a lot) is marked as a failed job with one task"""
        fn = os.path.join(FIXTURE_DIR, 'trace_files/job-fail-task1-manyretry.txt')
        items = _get_contents(fn)
        self.assertFalse(items.all_complete(), 'Not all tasks completed')
        self.assertTrue(items.any_failed(), 'Some tasks report failure as the highest state')

        self.assertEqual(items.final_status(), TaskStatus.FAILED, 'Final trace status is FAILED')
        self.assertEqual(len(items.consolidate()), 1, 'One task was run')

    def test_fail_multi_tasks_mixed_results(self):
        """
        A job has a mix of tasks: a success, followed by a second branch that forks (1 failed + 1 abort).
        Since one task maxed out at "fail", it is a failed job.
        """
        fn = os.path.join(FIXTURE_DIR, 'trace_files/job-fail-task2-retries-and-aborts.txt')
        items = _get_contents(fn)
        self.assertFalse(items.all_complete(), 'Not all tasks completed')
        self.assertTrue(items.any_failed(), 'Some tasks report failure as the highest state')

        self.assertEqual(items.final_status(), TaskStatus.FAILED, 'Final trace status is FAILED')
        self.assertEqual(len(items.consolidate()), 3, 'Three tasks were run')

