"""
Test compute backend features

We don't really want to be executing real jobs. Instead, this package is focused on things like state reconciliation
 (based on fixture files and mock status codes)
"""
import os

from django.test import TestCase

from nf_executor.api.enums import JobStatus
from nf_executor.api.tests.factories import JobFactory
from nf_executor.nextflow.runners import AbstractRunner, get_runner
from nf_executor.nextflow.runners.storage import LocalStorage

# A library of fixture files for various situations

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '../fixtures/trace_files')


class PseudoRunner(AbstractRunner):
    """An abstract runner that can participate in "status check" events using a hardcoded exit status and tracefile"""
    def __init__(self, *args, exit_code=None, trace_fn=None, **kwargs):
        # Flags used to mock out certain behaviors
        self._exit_code = exit_code  # What te executor says really happened
        self._trace = trace_fn

        super().__init__(*args, **kwargs)

    def _check_run_state(self) -> JobStatus:
        """There is no run state to query"""
        if self._exit_code is None:
            return JobStatus.unknown
        elif self._exit_code == 0:
            return JobStatus.completed
        elif self._exit_code == -1:
            # This is a mock class, we don't need to take exit codes too literally
            return JobStatus.started
        else:
            return JobStatus.error

    def _trace_fn(self, run_id: str) -> str:
        """We're ignoring storages and going straight to a fixture file"""
        return self._stable_storage.relative(self._trace)

    ####
    # Methods not used by mock
    def _cancel_to_engine(self) -> bool:
        return True

    def _submit_to_engine(self, callback_url: str, *args, **kwargs) -> str:
        return 'the check is in the mail'


def make_runner(job, exit_code, trace_choice):
    traces = {
        'SUCCESS': 'job-success-with-task-retries.txt',
        'FAILURE': 'job-fail-task2-retries-and-aborts.txt',
        'UNKNOWN': 'nonexistent/nothere.txt'
    }
    return PseudoRunner(
        job,
        LocalStorage(os.path.join(FIXTURE_DIR)),
        exit_code=exit_code,
        trace_fn=traces[trace_choice]
    )


class TestRunnerReconciliation(TestCase):
    """Test the ability of a job runner to determine exit status"""

    ###
    # Already resolved
    def test_resolved_job_status_is_obvious(self):
        """If the database says job was previously resolved, nothing else will even be checked"""
        scenarios = [JobFactory(is_completed=True), JobFactory(is_canceled=True)]

        for j in scenarios:
            runner = make_runner(j, 42, 'UNKNOWN')
            actual, is_ok = runner.reconcile_job_status(save=False)
            self.assertTrue(is_ok, f'Reconciliation favors the actual job status for job {j.status}')

    ###
    # Cancel functionality, including reconciliation of pending cancel status. Note: trace file never used to make
    #   decisions here. Either the job is still running, or it isn't.
    def test_cancel_pending_changes_to_canceled_by_exit_code(self):
        """A job was pending cancellation, but new information from the executor upgrades that status"""
        job = JobFactory(is_cancel_pending=True)
        runner = make_runner(job, 1, 'UNKNOWN')

        actual, is_ok = runner.reconcile_job_status(save=False)
        self.assertFalse(is_ok, f'Pending cancel is resolved based on exit code')
        self.assertEqual(actual, JobStatus.canceled, f'Pending cancel is resolved based on exit code')

    def test_cancel_pending_if_no_records_mark_canceled(self):
        """
        A job was pending cancellation, but we've lost all records of either trace file or exit code
        TODO: I have mixed feelings about this one. We're going to be generous and assume that if the cancel signal
            was sent, then if there are no records, it's effectively dead.
            If we have a lot of dropped signals, we might consider special handling for "unknown" instead.
        """
        job = JobFactory(is_cancel_pending=True)
        runner = make_runner(job, None, 'UNKNOWN')  # No information on resolution is available

        actual, is_ok = runner.reconcile_job_status(save=False)
        self.assertFalse(is_ok, f'We said to kill th ')
        self.assertEqual(actual, JobStatus.canceled, f'Pending cancel cannot be resolved and is set to unknown')

    def test_cancel_pending_still_running_by_exit_code(self):
        """A job was pending cancellation, but new information from the executor upgrades that status"""
        job = JobFactory(is_cancel_pending=True)
        runner = make_runner(job, -1, 'UNKNOWN')

        actual, is_ok = runner.reconcile_job_status(save=False)
        self.assertTrue(is_ok, f'Job is still running, so cancel is still pending')

    ####
    # Reconciliation required
    def test_submitted_job_actually_completed_by_exit_code(self):
        """We lost track of a job at submission time, and resolve as "success" later based on exit status"""
        scenarios = [JobFactory(is_submitted=True), JobFactory(is_started=True)]

        for job in scenarios:
            runner = make_runner(job, 0, 'UNKNOWN')

            actual, is_ok = runner.reconcile_job_status(save=False)
            self.assertFalse(is_ok, f'Lost job with initial status {job.status} requires reconciliation')
            self.assertEqual(actual, JobStatus.completed,
                             f'Lost job with initial status {job.status} is resolved based on exit code')

    def test_submitted_job_actually_completed_by_trace(self):
        """We lost track of a job at submission time, and resolve as "success" later based on trace"""
        scenarios = [JobFactory(is_submitted=True), JobFactory(is_started=True)]

        for job in scenarios:
            runner = make_runner(job, None, 'SUCCESS')

            actual, is_ok = runner.reconcile_job_status(save=False)
            self.assertFalse(is_ok, f'Lost job with initial status {job.status} requires reconciliation')
            self.assertEqual(actual, JobStatus.completed,
                             f'Lost job with initial status {job.status} is resolved based on trace')

    def test_submitted_job_actually_failed_by_exit_code(self):
        """We lost track of a job at submission time, and resolve as "failed" later based on exit status"""
        scenarios = [JobFactory(is_submitted=True), JobFactory(is_started=True)]

        for job in scenarios:
            runner = make_runner(job, 1, 'UNKNOWN')

            actual, is_ok = runner.reconcile_job_status(save=False)
            self.assertFalse(is_ok, f'Lost job with initial status {job.status} requires reconciliation')
            self.assertEqual(actual, JobStatus.error,
                             f'Lost job with initial status {job.status} is resolved based on exit code')

    def test_submitted_job_actually_failed_by_trace(self):
        """We lost track of a job at submission time, and resolve as "failure" later based on trace file"""
        scenarios = [JobFactory(is_submitted=True), JobFactory(is_started=True)]

        for job in scenarios:
            runner = make_runner(job, None, 'FAILURE')

            actual, is_ok = runner.reconcile_job_status(save=False)
            self.assertFalse(is_ok, f'Lost job with initial status {job.status} requires reconciliation')
            self.assertEqual(actual, JobStatus.error,
                             f'Lost job with initial status {job.status} is resolved based on trace')

    def test_submitted_job_cannot_be_resolved(self):
        """We lost track of a job at submission time, and resolve as "unknown" later when all records are lost"""
        scenarios = [JobFactory(is_submitted=True), JobFactory(is_started=True)]

        for job in scenarios:
            runner = make_runner(job, None, 'UNKNOWN')

            actual, is_ok = runner.reconcile_job_status(save=False)
            self.assertFalse(is_ok, f'Lost job with initial status {job.status} requires reconciliation')
            self.assertEqual(actual, JobStatus.unknown,
                             f'Lost job with initial status {job.status} cannot be resolved')
