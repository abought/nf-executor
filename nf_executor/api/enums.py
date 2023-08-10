from enum import Enum, IntEnum


class ModelHelper:
    @classmethod
    def choices(cls: Enum):
        return [(i.value, i.name) for i in cls]


class JobStatus(ModelHelper, IntEnum):
    """
    Known nextflow Workflow statuses: https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http
    """
    started = 1
    error = 2  # Is this a task or job state? NF docs unclear
    completed = 3
    # Not provided by nextflow- managed by this system
    submitted = 0
    canceled = 4


class TaskStatus(ModelHelper, IntEnum):
    """Known nextflow Task statuses: https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http"""
    process_submitted = 0
    process_started = 1
    process_completed = 2
