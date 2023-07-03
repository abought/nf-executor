from enum import IntEnum


class JobStatus(IntEnum):
    """
    Known nextflow Workflow statuses: https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http
    """
    started = 1
    error = 2
    completed = 3
    # Not provided by nextflow- managed by this system
    submitted = 0
    canceled = 4


class TaskStatus(IntEnum):
    """Known nextflow Task statuses: https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http"""
    process_submitted = 0
    process_started = 1
    process_completed = 2
