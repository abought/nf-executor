"""
Parse various types of tracelog events from Nextflow

These parsers are used for event reconciliation, and hence they populate a data container rather than a model
"""
import collections
import dataclasses as dc
from datetime import datetime

from nf_executor.api import enums
from nf_executor.nextflow.exceptions import TaskStateException


def parse_none(value, as_type=None):
    """Nextflow trace file uses `-` as a placeholder when no value was provided"""
    if value == '-':
        return None

    if as_type:
        value = as_type(value)
    return value


@dc.dataclass
class NFTraceEvent:
    task_id: str
    hash: str
    native_id: str
    name: str
    status: enums.TaskStatus
    exit_code: int
    submit: datetime
    duration: str  # reported with a human suffix
    realtime: str
    pct_cpu: float
    peak_rss: float
    peak_vmem: float
    rchar: int
    wchar: int

    def __post_init__(self):
        """Clean up datatypes where parsing is needed"""
        self.exit_code = parse_none(self.exit_code, as_type=int)
        self.submit = datetime.fromisoformat(self.submit)  # type: ignore
        self.status = enums.TaskStatus[self.status]  # type: ignore

        self.pct_cpu = parse_none(self.pct_cpu, as_type=float)
        self.peak_rss = parse_none(self.peak_rss, as_type=float)
        self.peak_vmem = parse_none(self.peak_vmem, as_type=float)
        self.rchar = parse_none(self.rchar, as_type=int)
        self.wchar = parse_none(self.wchar, as_type=int)

    # def fill_model(self, task):
    #     pass


class TraceList(collections.UserList):
    def consolidate(self):
        final = {}
        for item in self.data:
            prev = final.get(item.name)  # WARNING: ASSUMES name is unique per task; IDs are new per retry of same task
            if not prev or (item.status >= prev.status):
                final[item.name] = item
        return TraceList(final.values())

    def any_aborted(self):
        """
        Did any tasks report abort as the last/highest state?
        (This can mean either that one task hard failed, OR that the whole job was canceled)
        """
        return any(
            i.status == enums.TaskStatus.ABORTED for
            i in self.consolidate()
        )

    def any_failed(self):
        """Did any tasks report failure as the last/highest state?"""
        return any(
            i.status == enums.TaskStatus.FAILED
            for i in self.consolidate()
        )

    def all_complete(self, items=None):
        """Do all tasks report success as the last/highest state?"""
        if not items:
            items = self.consolidate()
        return all(
            i.status == enums.TaskStatus.COMPLETED
            for i in items
        )

    def final_status(self):
        """
        Report the final status OF TASKS, as inferred from trace files

        There may be cases where task status != job status, eg if nextflow crashed halfway through. Combine the output
            of this method with other info (from the job runner) as needed.
        """
        items = self.consolidate()
        if self.all_complete(items):
            return enums.TaskStatus.COMPLETED

        # If not all tasks are complete, then they are either running or they failed.
        # It's possible that failures just mean a retry was scheduled: this only reports final task status
        running = [i.status for i in items if i.status <= enums.TaskStatus.RUNNING]
        errs = [
            i.status for i in items
            if enums.TaskStatus.RUNNING < i.status <= enums.TaskStatus.FAILED  # Note: May include retries-in-progress
        ]

        if len(running):
            return max(running)

        # If nothing is running or planned, assume the final status is the error state
        if len(errs):
            return max(errs)

        # If not completed, nothing is running, and no errors: What gives? Assume that trace files are never empty.
        raise TaskStateException('Trace file cannot be resolved to determine job state')


def parse_tracelog(raw_content: str) -> TraceList[NFTraceEvent]:
    """
    Parse a nextflow tracelog into data tuples.

    Optionally, can consolidate the event stream so that only the last reported status (assumed rank ordering)
        is returned. This is useful when reconciling newest DB state with tracelog.
    """
    return TraceList(
        NFTraceEvent(*line.strip().split('\t'))
        for line in raw_content.splitlines()[1:]  # Ignore header row present in trace file format
    )
