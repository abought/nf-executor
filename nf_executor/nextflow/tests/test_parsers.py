from datetime import datetime
import json
import os.path

from django.test import TestCase

from nf_executor.api.enums import JobStatus, TaskStatus

from nf_executor.api.tests.factories import (
    JobFactory,
    TaskFactory,
)

from nf_executor.nextflow import parsers

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def get_job_started_event() -> dict:
    fn = os.path.join(FIXTURE_DIR, 'started.json')
    with open(fn, 'r') as f:
        content = json.load(f)
    return content


def get_job_completed_event() -> dict:
    fn = os.path.join(FIXTURE_DIR, 'completed.json')
    with open(fn, 'r') as f:
        content = json.load(f)
    return content


def get_task_submitted_event() -> dict:
    fn = os.path.join(FIXTURE_DIR, 'process_submitted.json')
    with open(fn, 'r') as f:
        content = json.load(f)
    return content


def get_task_started_event() -> dict:
    fn = os.path.join(FIXTURE_DIR, 'process_started.json')
    with open(fn, 'r') as f:
        content = json.load(f)
    return content


def get_task_completed_event() -> dict:
    fn = os.path.join(FIXTURE_DIR, 'process_completed.json')
    with open(fn, 'r') as f:
        content = json.load(f)
    return content


def get_full_event_stream() -> list[dict]:
    fn = os.path.join(FIXTURE_DIR, 'nextflow-mock-full-eventstream.json')
    with open(fn, 'r') as f:
        content = json.load(f)
    return content


class JobStatusParserTests(TestCase):
    def test_job_started(self):
        new_job = JobFactory(is_submitted=True)
        self.assertEqual(
            new_job.status, JobStatus.submitted.value,
            'Pre test sanity check'
        )

        payload = get_job_started_event()
        filled_job = parsers.parse_event(new_job, payload)

        filled_job.save()
        filled_job.refresh_from_db()

        self.assertEqual(
            filled_job.started_on,
            datetime.fromisoformat(payload['utcTime']),
            'Populated correct start time'
        )

        self.assertEqual(
            filled_job.status, JobStatus.started.value,
            'Job status set to started'
        )

    def test_job_completed(self):
        job = JobFactory(is_started=True)

        self.assertEqual(
            job.status, JobStatus.started.value,
            'Pre test sanity check'
        )

        payload = get_job_completed_event()
        filled_job = parsers.parse_event(job, payload)

        filled_job.save()
        filled_job.refresh_from_db()

        self.assertEqual(
            filled_job.completed_on,
            datetime.fromisoformat(payload['utcTime']),
            'Populated correct completion time'
        )

        self.assertEqual(
            filled_job.status, JobStatus.completed.value,
            'Job status set to completed'
        )

        self.assertNotEquals(filled_job.duration, 0, 'Duration populated')
        self.assertNotEquals(filled_job.succeed_count, 0, 'Succ count populated')


class TaskStatusParserTests(TestCase):
    def setUp(self):
        self.running_job = JobFactory(is_started=True)

    def test_task_submission_creates_new_task(self):
        self.assertEqual(self.running_job.task_set.count(), 0, 'Job has no tasks when created')

        payload = get_task_submitted_event()
        task = parsers.parse_event(self.running_job, payload)

        task.save()
        # self.running_job.refresh_from_db()  # update relationship set

        self.assertEqual(self.running_job.task_set.count(), 1, 'Job has one task after event')

    def test_task_submission_out_of_order(self):
        """If events arrive out of order, verify that task submission event doesn't overwrite newer information"""
        task = TaskFactory(job=self.running_job, task_id=1, is_completed=True)

        payload = get_task_submitted_event()
        revised_task = parsers.parse_event(self.running_job, payload)

        revised_task.save()
        self.running_job.refresh_from_db()  # update relationship set

        self.assertEqual(
            self.running_job.task_set.count(),
            1,
            'Existing event with same task ID was updated in place'
        )

        self.assertEqual(
            revised_task.status,
            TaskStatus.process_completed.value,
            'Higher status is not overridden'
        )

    def test_task_start_updates_record(self):
        task = TaskFactory(job=self.running_job, task_id=1, is_submitted=True)

        payload = get_task_started_event()
        revised_task = parsers.parse_event(self.running_job, payload)

        revised_task.save()
        self.running_job.refresh_from_db()  # update relationship set

        self.assertEqual(
            self.running_job.task_set.count(),
            1,
            'Existing event with same task ID was updated in place'
        )

        self.assertEqual(
            revised_task.status,
            TaskStatus.process_started.value,
            'Task status of existing record was updated in place'
        )

        self.assertEqual(
            revised_task.native_id,
            28560,
            'Payload fields were used to populate record'
        )

    def test_task_start_creates_record_if_out_of_order(self):
        self.assertEqual(
            self.running_job.task_set.count(),
            0,
            'No task records before event received'
        )
        payload = get_task_started_event()
        new_task = parsers.parse_event(self.running_job, payload)

        new_task.save()
        self.running_job.refresh_from_db()  # update relationship set

        self.assertEqual(
            self.running_job.task_set.count(),
            1,
            'One task record was created'
        )

    def test_task_complete_updates_record(self):
        task = TaskFactory(job=self.running_job, task_id=1, is_completed=True)

        payload = get_task_completed_event()
        revised_task = parsers.parse_event(self.running_job, payload)

        revised_task.save()
        self.running_job.refresh_from_db()  # update relationship set

        self.assertEqual(
            self.running_job.task_set.count(),
            1,
            'Existing event with same task ID was updated in place'
        )

        self.assertEqual(
            revised_task.status,
            TaskStatus.process_completed.value,
            'Task status of existing record was updated in place'
        )

        self.assertEqual(
            revised_task.exit_code,
            0,
            'Payload fields were used to populate record'
        )

    def test_task_complete_creates_record_if_out_of_order(self):
        self.assertEqual(
            self.running_job.task_set.count(),
            0,
            'No task records before event received'
        )
        payload = get_task_completed_event()
        new_task = parsers.parse_event(self.running_job, payload)

        new_task.save()
        self.running_job.refresh_from_db()  # update relationship set

        self.assertEqual(
            self.running_job.task_set.count(),
            1,
            'One task record was created'
        )


class FullSequenceParserTests(TestCase):
    """Test a full sequence"""
    def _same_result_helper(self, events):
        """Given a payload in any order, verifies that the same tests will pass"""
        # TODO: Stub. We can fill this in more aggressively later.
        job = JobFactory(is_submitted=True)

        for record in events:
            item = parsers.parse_event(job, record)
            item.save()

        job.refresh_from_db()

        self.assertEqual(job.task_set.count(), 3, 'Three task records created')
        self.assertEqual(
            job.task_set.filter(status=TaskStatus.process_completed.value).count(),
            3,
            'All task records completed'
        )
        self.assertEqual(job.status, JobStatus.completed.value, 'Job resolves to completed')

    def test_full_event_stream_creates_expected_tasks(self):
        payload = get_full_event_stream()
        self._same_result_helper(payload)

    def test_reversed_full_event_stream_creates_expected_tasks(self):
        """Pathological case: even if events are handled out of order, final DB state should be the same"""
        payload = reversed(get_full_event_stream())
        self._same_result_helper(payload)
