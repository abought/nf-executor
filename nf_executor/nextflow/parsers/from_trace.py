"""
Parse various types of tracelog events from Nextflow

These parsers are used for event reconciliation, and hence they populate a data container rather than a model
"""
import dataclasses as dc
from datetime import datetime

from nf_executor.api import enums


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


def parse_tracelog(raw_content: str, consolidate=False):
    """
    Parse a nextflow tracelog into data tuples.

    Optionally, can consolidate the event stream so that only the last reported status (assumed rank ordering)
        is returned. This is useful when reconciling newest DB state with tracelog.
    """
    records = [
        NFTraceEvent(*line.strip().split('\t'))
        for line in raw_content.splitlines()[1:]  # ignore header row
    ]

    if consolidate:
        final = {}
        for item in records:
            prev = final.get(item.task_id)
            if not prev or (item.status > prev.status):
                final[item.task_id] = item
        records = list(final.values())

    return records
