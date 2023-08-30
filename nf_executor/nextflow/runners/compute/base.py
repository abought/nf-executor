import abc
import dataclasses as dc
import json
import logging
import typing as ty

from django.conf import settings

from nf_executor.api import enums, models
from nf_executor.api.enums import JobStatus

from nf_executor.nextflow import exceptions as exc
from nf_executor.nextflow.parsers.from_trace import parse_tracelog
from nf_executor.nextflow.runners.storage.base import AbstractJobStorage

logger = logging.getLogger(__name__)


@dc.dataclass
class TaskCounter:
    submitted: int
    started: int
    completed: int


class AbstractExecutor(abc.ABC):
    """
    Handle all aspects of running a job on a particular platform: AWS batch, local subprocess, slurm, etc

    Every job has a LOCAL record of state (the database list of execution events) and a REMOTE record of state
        (what's actually going on: slurm, subprocess, AWS batch, etc). The remote updates local state via a callback URI
        that can parse nextflow events: https://www.nextflow.io/docs/latest/tracing.html#weblog-via-http

    Optionally, the user can set a working directory that is local to the host where the job runs. This is a
      destination for temporary output files during the job run.

    Unfortunately, this means that if the `nf_executor` service is down, state can get out of sync. The NF http feature
        isn't smart enough to talk to an external queue like RabbitMQ (limited control over payload format), so syncing
         is accomplished by a more manual process. (usually a celery task)
    """
    def __init__(
            self,
            storage: AbstractJobStorage,
            workdir=settings.NF_EXECUTOR['workdir'],
            *args,
            **kwargs
    ):
        self._stable_storage = storage  # Persistent files like job config files and logs: exist before and after job
        self.workdir = workdir

    ##########
    # Public interface
    def run(
            self,
            job: models.Job,
            params: dict,
            callback_uri,
            *args,
            **kwargs
    ) -> models.Job:
        """
        Run a new task for the specified workflow in this executor

        All nextflow tasks report execution via an HTTP callback URI
        """
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
            params_ok = False
            logger.exception(f"Could not write job parameters file in {job.logs_dir}. Check if volume is readable.")

        if not params_ok:
            # This may be a canary for unreachable working directory, so we shouldn't allow the job to proceed.
            job.status = enums.JobStatus.error
            job.save()
            return job

        try:
            executor_id = self._submit_to_engine(job, callback_uri, *args, **kwargs)
            job.executor_id = executor_id
        except:
            logger.exception(f"Error while submitting job {job.run_id}")
            job.status = enums.JobStatus.error

        job.save()  # Second save: record work scheduled by system, incl result of attempts to schedule job
        return job

    def check_job_status(self, job: models.Job, force=False) -> enums.JobStatus:
        """
        Report running or not.

        A status update can optionally force checking of remote records. (typically only done via nightly celery task)
        """
        if force:
            return self._query_remote_state(job)
        else:
            return self._query_local_state(job)

    def reconcile_job_status(self, job: models.Job) -> (enums.JobStatus, bool):
        """Check job status, and force updates to the DB as needed"""
        actual = self._query_remote_state(job)
        expected = self._query_local_state(job)

        is_ok = actual == expected
        if not is_ok:
            logger.warning(f"Job status conflict for {job.run_id}. Will update from {expected} to {actual}")
            job.status = actual
            job.save()

        return (actual, is_ok)

    def check_job_tasks(self, job: models.Job) -> TaskCounter:
        """
        Reports number of tasks currently running for this job, based on database event records.

        NOTE: Not a reliable progress bar, because Nextflow may not know all work that has to be done at the start.
            (Example: during QC phase, NF won't have reported scheduling imputation chunks yet)
        """
        if job.status == enums.JobStatus.completed:
            return TaskCounter(0, 0, job.succeed_count)
        elif job.status in (enums.JobStatus.error, enums.JobStatus.canceled):
            return TaskCounter(0, 0, 0)

        return TaskCounter(
            # TODO: Replace with proper group by query once we have some records to test against
            #   https://stackoverflow.com/questions/19101665/how-to-do-select-count-group-by-and-order-by-in-django
            job.task_set.filter(status=enums.TaskStatus.SUBMITTED).count(),
            job.task_set.filter(status=enums.TaskStatus.RUNNING).count(),
            job.task_set.filter(status=enums.TaskStatus.COMPLETED).count(),
        )

    def cancel(self, job):
        raise NotImplementedError

    #######
    # Private / internal methods
    def _write_params(self, job: models.Job, params: dict):
        """
        Write a params file used by nextflow to the working directory
        """
        if params is None:
            params = {}

        path = self._params_fn(job)
        self._stable_storage.write_contents(
            path,
            json.dumps(params, indent=2)
        )

    def _generate_workflow_options(self, job: models.Job, callback_uri: str, *args, **kwargs) -> list[str]:
        """Generate the workflow options used by nextflow."""
        workflow_def = job.workflow.definition_path
        logs_dir = job.logs_dir

        params_fn = self._params_fn(job)
        trace_fn = self._trace_fn(job)
        log_fn = self._stable_storage.relative(f'nf_log_{job.run_id}.txt')
        report_fn = self._stable_storage.relative(f'report-{job.run_id}.html')

        args = [
            'nextflow',
            '-log', log_fn,
            'run', workflow_def,
            '-params-file', params_fn,
            '-name', job.run_id,
            '-with-trace', trace_fn,
            '-with-weblog', callback_uri,
            '-with-report', report_fn,
            # Workflow definition and report files are written to root of workdir location, other files go under that
            '-work-dir', self.workdir,
        ]

        return args

    @abc.abstractmethod
    def _submit_to_engine(self, job: models.Job, callback_uri: str, *args, **kwargs) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def _cancel_to_engine(self, job: models.Job) -> bool:
        """
        Submit cancel signals for the job (and subprocesses if appropriate)

        Ideally, this should also schedule a celery process to confirm the kill signal after a specified time
        """
        raise NotImplementedError

    def _query_local_state(self, job: models.Job) -> enums.JobStatus:
        """Rely on the DB for job execution status. This is almost always how external tools will check status"""
        return enums.JobStatus(job.status)

    def _query_remote_state(self, job: models.Job) -> ty.Union[JobStatus, int]:
        """
        Determine the job status from three questions:

         1. Is it running?
         2. Does the database agree?
         3. If it is not running, can we infer job state by looking at the trace file records?
        """
        dbv = job.status
        if JobStatus.is_resolved(dbv):
            # If the job has been marked as resolved in any form, assume no further info needed from exec engine
            return dbv

        actual_status = self._check_run_state(job)

        if dbv == JobStatus.cancel_pending:
            # An explicit cancel request takes precedence over other status.
            if JobStatus.is_active(actual_status):
                # The nextflow executor is still running, so we are "still cancel pending"
                return dbv
            else:
                # Cancel has succeeded
                return JobStatus.canceled

        if actual_status != JobStatus.unknown:
            # If the executor can tell us exit code / completion, great! Use that.
            return actual_status

        # If the executor can't tell us status, we can try to guess job result from a trace file. This is especially
        #   useful for executors like "subprocess" where we may not have exit code info after process is ended.

        # Job is not running, and this is not explained by recorded callback events. Reconcile status using trace log!
        trace_fn = self._trace_fn(job)
        try:
            trace_contents = self._stable_storage.read_contents(trace_fn)
        except:
            # No records of process running, and no records of output. Reconciliation is not possible.
            # Flag permanent loss of records for auditing/ retry
            logger.error(f'Could not locate trace file expected to reconcile job {job.run_id}')
            return JobStatus.unknown

        parsed = parse_tracelog(trace_contents)
        resolved = parsed.final_status()

        return JobStatus.task_to_job(resolved)

    @abc.abstractmethod
    def _check_run_state(self, job: models.Job) -> JobStatus:
        """
        Is the job actively running on the executor?

        Returns a job status code, which should be one of {submitted, started, error, completed, unknown}. This can
         check both active process and any queue as needed.
        """
        raise NotImplementedError

    ##############
    # Helpers: names of key files that are used in multiple places (e.g. writing a trace file, then checking it)
    def _params_fn(self, job: models.Job) -> str:
        """Path to params file"""
        return self._stable_storage.relative(f'nextflow_params_{job.run_id}.json')

    def _trace_fn(self, job: models.Job) -> str:
        """Path to nextflow execution trace file"""
        return self._stable_storage.relative(f'trace_{job.run_id}.txt')
