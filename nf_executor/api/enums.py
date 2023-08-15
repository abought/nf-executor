from enum import Enum, IntEnum


class ModelHelper:
    @classmethod
    def choices(cls: Enum):
        return [(i.value, i.name) for i in cls]


class JobStatus(ModelHelper, IntEnum):
    """
    Known nextflow Workflow statuses: https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http
    """
    started = 10
    error = 20  # Is this a task or job state? NF docs unclear
    completed = 30
    # Not provided by nextflow- managed by this system
    submitted = 0  # Nextflow was scheduled to run, but we have not yet received events

    cancel_pending = 40  # Cancel request initiated but not yet confirmed by execution engine
    unknown = 45  # Job state could not be reconciled, eg because of lost records or failure to query execution engine
    canceled = 50  # User manually terminated job and ending was confirmed


class TaskStatus(ModelHelper, IntEnum):
    """Known nextflow Task statuses: https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http"""
    process_submitted = 0
    process_started = 10
    process_completed = 20
