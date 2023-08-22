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
    completed = 50

    # Not provided by nextflow- managed by this system
    submitted = 0  # Nextflow was scheduled to run, but we have not yet received events
    cancel_pending = 30  # Cancel request initiated but not yet confirmed by execution engine
    unknown = 35  # Job state could not be reconciled, eg because of lost records or failure to query execution engine
    canceled = 40  # User manually terminated job and ending was confirmed


class TaskStatus(ModelHelper, IntEnum):
    """
    Known nextflow Task statuses: two ways of tracing provide different enums

     Lowercase are used by HTTP;
        https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http

    Uppercase (may) be used by trace. It seems that some runners only ever write the completed items:
        https://www.nextflow.io/docs/latest/tracing.html#trace-report

    The final numeric values are our best guess (in terms of both ordinal ranking, and mapping across systems). They do not represent official doc statements
    """
    # TRACE log statuses
    NEW = 0
    SUBMITTED = 10
    RUNNING = 20
    ABORTED = 30
    FAILED = 40
    COMPLETED = 50

    # HTTP log statuses. Alignment with trace log statuses is best-guess.
    #   Interesting to note that not all task states are reported!
    process_submitted = 10
    process_started = 20
    process_completed = 50
