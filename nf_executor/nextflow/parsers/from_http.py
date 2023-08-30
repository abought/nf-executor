"""
Parse various types of weblog-via-http events from Nextflow

These parsers are intended to update a model directly, and hence they populate existing model classes

TODO: In the future, we want to use the same data container logic for both HTTP and trace logs. Unfortunately,
    the event data available is so different that this is hard to reconcile right now.
"""
from datetime import datetime
import json
import typing as ty

from nf_executor.api import enums, models
from nf_executor.nextflow.exceptions import UnknownEventException


def parse_time(payload: dict) -> datetime:
    """Nextflow records store event time as utc string field"""
    return datetime.fromisoformat(payload['utcTime'])


def job_started(job: models.Job, payload: dict) -> models.Job:
    """
    Update job status. If events are out of order, this is the authority for start time but should not override a later status event
    """
    job.started_on = parse_time(payload)
    job.status = max(job.status, enums.JobStatus.started)  # in case of out of order events, don't overwrite

    return job


def job_error(job: models.Job, payload: dict) -> models.Job:
    """An error code overrides any other status"""
    job.status = enums.JobStatus.error
    return job


def job_completed(job: models.Job, payload: dict) -> models.Job:
    """
    Job completion notice.
    Override any other status (incl error state) because there are data cleanup ramifications

    In the future, we'd like to treat this like a state machine (only allow transition if job state was started)

    In practice, out-of-order event stream processing can't be ruled out, so...
    """
    metadata = payload['metadata']

    job.completed_on = parse_time(payload)
    job.status = enums.JobStatus.completed

    # Capture metadata seen only in job completion events
    job.duration = metadata['workflow']['duration']
    job.succeed_count = metadata['workflow']['workflowStats']['succeededCount']
    job.retries_count = metadata['workflow']['workflowStats']['retriesCount']

    return job


def task_submit(job: models.Job, payload: dict) -> models.Task:
    """
    Create a task record when a process is submitted.

    Handle possible race condition where later events handled first.
    """
    metadata = payload['trace']
    task_id = metadata['task_id']
    task, _ = models.Task.objects.get_or_create(job=job, task_id=task_id)

    # Submission event is always the source of truth for these fields
    task.submitted_on = parse_time(payload)
    task.name = metadata['name']

    # Values that might conflict under race condition
    task.status = max(task.status, enums.TaskStatus.process_submitted)

    return task


def task_start(job: models.Job, payload: dict) -> models.Task:
    """Update a task record once a task starts"""
    metadata = payload['trace']
    task_id = metadata['task_id']
    task, _ = models.Task.objects.get_or_create(job=job, task_id=task_id)

    # Start event is always the source of truth for these fields
    # TODO What happens if a task restarts/fails? Are restarts provided as a unique new task ID? If not, how should we track them for a more accurate picture of resource usage?
    task.native_id = metadata['native_id']
    task.started_on = parse_time(payload)

    # Values that might conflict under race condition
    task.status = max(task.status, enums.TaskStatus.process_started)

    return task


def task_complete(job: models.Job, payload: dict) -> models.Task:
    """
    Update a task record once a task completes. Completion does not mean success
    """
    metadata = payload['trace']
    task_id = metadata['task_id']
    task, _ = models.Task.objects.get_or_create(job=job, task_id=task_id)

    # Completion event is always the source of truth for these fields
    task.completed_on = parse_time(payload)
    task.exit_code = metadata['exit']  # Note: start events report a dummy value of 2^31-1 (aka max of a 32 bit signed int)

    # Values that might conflict under race condition
    task.status = max(task.status, enums.TaskStatus.process_completed)

    return task


def parse_event(job: models.Job, payload: ty.Union[str, dict]) -> ty.Union[models.Task, models.Job]:
    """Map an event name (from NF as string) into a Job or Task record, as appropriate"""
    known_events = {
        # According to NF doc defined enumeration, http events are fixed constants
        # Job events
        'started': job_started,
        'error': job_error,
        'completed': job_completed,
        # Task events
        'process_submitted': task_submit,
        'process_started': task_start,
        'process_completed': task_complete,
    }

    if isinstance(payload, (str, bytes)):
        payload = json.loads(payload)

    name = payload['event']
    try:
        parser = known_events[name]
    except KeyError:
        raise UnknownEventException(f"Unrecognized nextflow event type: `{name}`")

    return parser(job, payload)
