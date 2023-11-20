import abc
import dataclasses as dc
import json
import logging
import typing as ty

from django.conf import settings
from django.utils import timezone


from abc_impute.api import enums, models
from abc_impute.api.enums import JobStatus
from abc_impute.api.models import Job

from abc_impute.nextflow import exceptions as exc
from abc_impute.nextflow.parsers.from_trace import parse_tracelog
from abc_impute.nextflow.runners.storage.base import AbstractJobStorage

logger = logging.getLogger(__name__)


@dc.dataclass
class TaskCounter:
    submitted: int
    started: int
    completed: int


class AbstractRunner(abc.ABC):
    """
    Handle all aspects of running a job on a particular platform: AWS batch, local subprocess, slurm, etc

    Every job has a LOCAL record of state (the database list of execution events) and a REMOTE record of state
        (what's actually going on: slurm, subprocess, AWS batch, etc). The remote updates local state via a callback URI
        that can parse nextflow events: https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http

    Optionally, the user can set a working directory that is local to the host where the job runs. This is a
      destination for temporary output files during the job run.

    Unfortunately, this means that if the `abc_impute` service is down, state can get out of sync. The NF http feature
        isn't smart enough to talk to an external queue like RabbitMQ (limited control over payload format), so syncing
         is accomplished by a more manual process. (usually a celery task)
    """
    CONFIG_KEY = None

    def __init__(
            self,
            job: Job,
            storage: AbstractJobStorage,
            config=settings.NF_EXECUTOR.get(CONFIG_KEY, {}),
            *args,
            **kwargs
    ):
        self._job = job
        self._stable_storage = storage  # Persistent files like job config files and logs: exist before and after job
        self._config = config

    ##########
    # Public interface
    def run(
            self,
            params: dict,
            callback_url,
            *args,
            **kwargs
    ) -> models.Job:
        """
        Run a new task for the specified workflow in this executor

        All nextflow tasks report execution via an HTTP callback URI
        """
        job = self._job
        if not job.workflow:
            raise exc.BadJobException('Job must specify a valid workflow definition in order to run')

        if job.status != enums.JobStatus.submitted:
            # Restarts *must* be represented as a new job object, to avoid conflicting records of task events
            # Please don't try to be clever by just editing one field to bypass this.
            raise exc.StaleJobException

        try:
            self._write_params(job, params)
            params_ok = True
        except:
            # TODO: Replace logs_dir with alternative here
            params_ok = False
            logger.exception(f"Could not write job parameters file in {job.job_storage_root}. Check if volume is readable.")

        if not params_ok:
            # This may be a canary for unreachable working directory, so we shouldn't allow the job to proceed.
            job.status = enums.JobStatus.error
            job.save()
            return job

        try:
            executor_id = self._submit_to_engine(callback_url, *args, **kwargs)
            job.executor_id = executor_id
        except:
            logger.exception("Error while submitting job %s", job.run_id)
            job.status = enums.JobStatus.error

        job.save()  # Second save: record work scheduled by system, incl result of attempts to schedule job
        return job

    def check_job_status(self, job: models.Job, force=False) -> enums.JobStatus:
        """
        Report running or not.

        A status update can optionally force checking of remote records. (typically only done via nightly celery task)
        """
        if force:
            return self._query_remote_state()
        else:
            return self._query_local_state()

    def reconcile_job_status(self, save=True) -> ty.Tuple[enums.JobStatus, bool]:
        """Check job status, and force updates to the DB as needed"""
        job = self._job
        actual = self._query_remote_state()
        expected = self._query_local_state()

        is_ok = actual == expected
        if not is_ok and save:
            logger.warning(f"Job status conflict for {job.run_id}. Will update from {expected} to {actual}")
            job.status = actual
            job.save()

        return (actual, is_ok)

    def cancel(self) -> models.Job:
        job = self._job
        if not JobStatus.is_active(job.status):
            logger.info(f'Cancel request for job {job.run_id} was ignored because job is not in an active state')
            return job

        # First save: we tried to cancel
        logger.info(f'Manually killing job {job.run_id}')
        job.status = JobStatus.cancel_pending
        job.save()

        signal_accepted = self._cancel_to_engine()
        if not signal_accepted:
            logger.error(f'Failed to cancel job {job.run_id}')
            job.status = JobStatus.unknown
            job.save()
            return job

        # Second save: Update meta job fields once cancel signal confirmed
        job.expire_on = timezone.now()  # Tell background worker to clean up working directories
        job.completed_on = timezone.now()

        delta = job.completed_on - job.started_on
        job.duration = delta.seconds * 1000  # nf specifies in ms, and so do we

        job.save()
        return job

    #######
    # Private / internal methods
    def _write_params(self, job: models.Job, params: dict):
        """
        Write a params file used by nextflow to the working directory
        """
        if params is None:
            params = {}

        path = self._params_fn(job.run_id)
        self._stable_storage.write_contents(
            path,
            json.dumps(params, indent=2)
        )

    @abc.abstractmethod
    def _submit_to_engine(self, callback_url: str, *args, **kwargs) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def _cancel_to_engine(self) -> bool:
        """
        Submit cancel signals for the job (and subprocesses if appropriate). The return value typically means
            "a request to kill was acknowledged". It does not guarantee that the process or dependent tasks are stopped.

        Ideally, this should also schedule a celery process to confirm the kill signal after a specified time
        """
        raise NotImplementedError

    def _query_local_state(self) -> enums.JobStatus:
        """Rely on the DB for job execution status. This is almost always how external tools will check status"""
        return enums.JobStatus(self._job.status)

    def _query_remote_state(self) -> ty.Union[JobStatus, int]:
        """
        Determine the job status from three questions:

         1. Is it running?
         2. Does the database agree?
         3. If it is not running, can we infer job state by looking at the trace file records?
        """
        job = self._job

        dbv = job.status
        if JobStatus.is_resolved(dbv):
            # If the job has been marked as resolved in any form, assume no further info needed from exec engine
            return dbv

        actual_status = self._check_run_state()

        if dbv == JobStatus.cancel_pending:
            # An explicit cancel request takes precedence over other status.
            if JobStatus.is_active(actual_status):
                # The nextflow executor is still running, so we are "still cancel pending"
                return JobStatus.cancel_pending
            else:
                # Any other executor status, incl "unknown", is taken to mean that cancel has succeeded
                return JobStatus.canceled

        if actual_status != JobStatus.unknown:
            # If the executor can tell us running state or completion (exit code 0), great! Use that.
            return actual_status

        # If the executor can't tell us status, we can try to guess job result from a trace file. This is especially
        #   useful for executors like "subprocess" where we may not have exit code info after process is ended.

        # Job is not running, and this is not explained by recorded callback events. Reconcile status using trace log!
        trace_fn = self._trace_fn(job.run_id)
        try:
            trace_contents = self._stable_storage.read_contents(trace_fn)
        except:
            # No records of process running, and no records of output. Reconciliation is not possible.
            # Flag permanent loss of records for auditing/ retry
            logger.error(f'Could not locate trace file expected to reconcile job {job.run_id}')
            return JobStatus.unknown

        try:
            parsed = parse_tracelog(trace_contents)
        except:
            logger.error(f'Could not parse trace file for job {job.run_id}')
            return JobStatus.unknown

        resolved = parsed.final_status()

        return JobStatus.task_to_job(resolved)

    @abc.abstractmethod
    def _check_run_state(self) -> JobStatus:
        """
        Is the job actively running on the executor?

        Returns a job status code, which should be one of {submitted, started, error, completed, unknown}. This can
         check both active process and any queue as needed.
        """
        raise NotImplementedError

    ##############
    # Helpers: names of key NF-specific files that are used in multiple places by the compute engine.
    def _params_fn(self, run_id: str) -> str:
        """Path to params file"""
        return self._stable_storage.relative(f'inputs', 'nextflow_params.json')

    def _work_dir(self, run_id: str) -> str:
        return self._stable_storage.relative(f'workdir/')

    def _trace_fn(self, run_id: str) -> str:
        """Path to nextflow execution trace file"""
        return self._stable_storage.relative('logs', f'trace_{run_id}.txt')

    def _report_fn(self, run_id: str) -> str:
        return self._stable_storage.relative('logs', f'report_{run_id}.html')

    def _log_fn(self, run_id: str) -> str:
        """Where log file will be written (or copied after run is complete, depending on executor)"""
        return self._stable_storage.relative('logs', f'nextflow_{run_id}.log')
