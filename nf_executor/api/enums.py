from enum import Enum, IntEnum

from nf_executor.nextflow.exceptions import TaskStateException


class ModelHelper:
    @classmethod
    def choices(cls: Enum):
        return [(i.value, i.name) for i in cls]


class JobStatus(ModelHelper, IntEnum):
    """
    Represent the status of a job
    """
    # Known nextflow Workflow statuses: https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http
    started = 10
    completed = 40
    error = 50  # NF http will send both an error AND a completed ("status: error") event. Error wins for final status.

    # Not provided by nextflow- managed by this system
    submitted = 0  # Nextflow was scheduled to run, but we have not yet received events
    cancel_pending = 20  # Cancel request initiated but not yet confirmed by execution engine
    unknown = 25  # Job state could not be reconciled, eg because of lost records or failure to query execution engine
    canceled = 30  # User manually terminated job and ending was confirmed

    @classmethod
    def is_active(cls, status) -> bool:
        """An active job: work that is running or planned. Pending cancels are neither active nor resolved"""
        return status in {cls.started, cls.submitted}

    @classmethod
    def is_resolved(cls, status) -> bool:
        return status in {cls.error, cls.completed, cls.canceled}

    @classmethod
    def task_to_job(cls, status: 'TaskStatus') -> 'JobStatus':
        """Resolve consolidated task status(es) into a final job status"""
        if status in {TaskStatus.NEW, TaskStatus.SUBMITTED, TaskStatus.RUNNING}:
            return cls.started

        if status in {TaskStatus.ABORTED, TaskStatus.FAILED}:
            return cls.error

        if status == TaskStatus.COMPLETED:
            return cls.completed

        raise TaskStateException(f'Unknown task status {status} cannot be mapped to a job state')


class TaskStatus(ModelHelper, IntEnum):
    """
    Known nextflow Task statuses: two ways of tracing provide different enums

     Lowercase are used by HTTP;
        https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http

    Uppercase (may) be used by trace. It seems that some runners only ever write the completed items:
        https://www.nextflow.io/docs/latest/tracing.html#trace-report

    The final numeric values are our best guess (in terms of both ordinal ranking, and mapping across systems).
    """
    # TRACE log statuses
    NEW = 0
    SUBMITTED = 10
    RUNNING = 20

    # These imply "task finished, and here's how"
    ABORTED = 30
    FAILED = 40
    COMPLETED = 50  # AFAICT, retries are represented as a new task ID, but just in case use C > F ordering

    @classmethod
    def is_active(cls, status):
        return status in {cls.NEW, cls.SUBMITTED, cls.RUNNING}

    @classmethod
    def is_resolved(cls, status):
        return status in {cls.ABORTED, cls.FAILED, cls.COMPLETED}
