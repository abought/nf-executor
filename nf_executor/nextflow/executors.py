import abc
import dataclasses as dc
import errno
import json
import logging
import os
import signal
import subprocess
import typing as ty

from django.utils import timezone

from nf_executor.api import enums, models

from nf_executor.nextflow import exceptions as exc

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

    Unfortunately, this means that if the `nf_executor` service is down, state can get out of sync. The NF http feature
        isn't smart enough to talk to an external queue like RabbitMQ (limited control over payload format), so syncing
         is accomplished by a more manual process. (usually a celery task)
    """
    def __init__(self, workflow: models.Workflow, *args, **kwargs):
        self.workflow = workflow

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
        if job.status != enums.JobStatus.submitted:
            # Restarts *must* be represented as a new job object, to avoid conflicting records of task events
            # Please don't try to be clever by just editing one field to bypass this.
            raise exc.StaleJobException

        try:
            self._write_params(job, params)
            params_ok = True
        except:
            params_ok = False
            logger.exception(f"Could not write job parameters file in {job.workdir}. Check if volume is readable.")

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

    def check_job_status(self, job: ty.Union[models.Job, str], force=False) -> enums.JobStatus:
        """
        Report running or not.

        A status update can optionally force checking of remote records. (typically only done via nightly celery task)
        """
        if isinstance(job, str):
            job = self._get_job_from_id(job)

        if force:
            return self._query_remote_state(job)
        else:
            return self._query_local_state(job)

    def check_job_tasks(self, job: ty.Union[models.Job, str]) -> TaskCounter:
        """
        Reports number of tasks currently running for this job, based on database event records.

        NOTE: Not a reliable progress bar, because Nextflow may not know all work that has to be done at the start.
            (Example: during QC phase, NF won't have reported scheduling imputation chunks yet)
        """
        if isinstance(job, str):
            job = self._get_job_from_id(job)

        if job.status == enums.JobStatus.completed:
            return TaskCounter(0, 0, job.succeed_count)
        elif job.status in (enums.JobStatus.error, enums.JobStatus.canceled):
            return TaskCounter(0, 0, 0)

        return TaskCounter(
            # TODO: Replace with proper group by query once we have some records to test against
            #   https://stackoverflow.com/questions/19101665/how-to-do-select-count-group-by-and-order-by-in-django
            job.task_set.filter(status=enums.TaskStatus.process_submitted).count(),
            job.task_set.filter(status=enums.TaskStatus.process_started).count(),
            job.task_set.filter(status=enums.TaskStatus.process_completed).count(),
        )

    def cancel(self, job):
        raise NotImplementedError

    #######
    # Private / internal methods
    def _get_job_from_id(self, job_id: str) -> models.Job:
        """Convenience method: allow status checks based on an ID, without a job object"""
        return models.Job.objects.filter(workflow=self.workflow).get(run_id=job_id)

    def _write_params(self, job: models.Job, params: dict):
        """
        Write a params file used by nextflow to the working directory
        """
        if params is None:
            params = {}

        path = self._params_fn(job.workdir)
        with open(path, 'w') as f:
            json.dump(params, f, indent=2)

    def _generate_workflow_options(self, job: models.Job, callback_uri: str, *args, **kwargs) -> list[str]:
        """Generate the workflow options used by nextflow."""
        workflow_path = self.workflow.definition_path
        workdir = job.workdir

        log_fn = os.path.join(workdir, f'nf_log_{job.run_id}.txt')
        trace_fn = os.path.join(workdir, f'trace_{job.run_id}.txt')
        report_fn = os.path.join(workdir, f'report-{job.run_id}.html')

        args = [
            'nextflow',
            'run', workflow_path,
            '-name', job.run_id,
            '-log', log_fn,
            '-with-trace', trace_fn,
            '-with-weblog', callback_uri,
            '-with-report', report_fn,
            # Workflow definition and report files are written to root of workdir location, other files go under that
            '-work-dir', os.path.join(workdir, 'intermediate'),
        ]

        params_fn = self._params_fn(job.workdir)
        if os.path.isfile(params_fn):
            args.extend(['-params-file', params_fn])

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

    @abc.abstractmethod
    def _query_remote_state(self, job: models.Job):
        """
        Queries the execution engine to determine if the task is running. This may use one or multiple artifacts.

        Must handle the following scenarios:
        - (error) Nextflow failed immediately upon start, and didn't bother to send an error to the monitor service
            (eg can happen with malformed params file)

        - (normal) Job not started, but execution engine says it is in the queue
        - (error) Job not started, and not in queue

        - (normal) Job running
        - (normal) Job not running: because it completed
        - (error) Job not running: DB says it should be, but executor says it isn't
        """
        raise NotImplementedError

    ##############
    # Helpers: names of key files that are used in multiple places (e.g. writing a trace file, then checking it)
    def _params_fn(self, workdir: str) -> str:
        """Path to params file"""
        return os.path.join(workdir, 'nextflow_params.json')


class SubprocessExecutor(AbstractExecutor):
    """
    Execute jobs in a subprocess worker that continues running on same host, even after the web app stops.
        ONLY used for dev/testing, and even then we should usually use celery.

    """
    def cancel(self, job: models.Job) -> models.Job:
        if job.status == enums.JobStatus.completed:
            logger.info(f'Cancel request for job {job.pk} was ignored because job already finished')
            return job

        logger.info(f'Manually killing job {job.pk}')
        # Note: this is dicey if NF doesn't actually kill the process, but subprocess executor isn't meant to be perfect.
        # TODO: How are tasks handled when NF is killed? Does this need special handling for different compute engines?

        job.status = enums.JobStatus.cancel_pending
        job.save()

        signal_accepted = self._cancel_to_engine(job)
        if not signal_accepted:
            job.status = enums.JobStatus.unknown
            job.save()
            return job

        # Update job fields once cancel confirmed
        # TODO move this to "cancel confirmed" celery task
        # TODO: Does nextflow send an event when the job is killed this way? (characterize how it works)
        job.expire_on = timezone.now()  # Tell background worker to clean up working directories
        job.completed_on = timezone.now()

        delta = job.completed_on - job.started_on
        job.duration = delta.seconds * 1000  # nf specifies in ms, and so do we

        job.save()
        return job

    def _query_remote_state(self, job: models.Job):
        raise NotImplementedError

    def _params_fn(self, workdir: str) -> str:
        # Subprocess executor uses a local filesystem, so unlike s3, it matters if prefix doesn't exist.
        if not os.path.isdir(workdir):
            os.makedirs(workdir)

        return super()._params_fn(workdir)

    def _submit_to_engine(self, job: models.Job, callback_uri: str, *args, **kwargs) -> str:
        """
        Submit a job to the execution engine

        TODO: Verify that NF executors can upload report/trace files to s3 and no further file handling is needed
        """
        args = self._generate_workflow_options(job, callback_uri, *args, **kwargs)

        logger.debug(f"Submitting job '{job.run_id}' to executor '{self.__class__.__name__}' with options {args}")

        sync = kwargs.get('sync', False)
        if sync:
            # Really really really only use this for debugging: web request shouldn't ever block on a child process
            proc = subprocess.run(args, capture_output=True)
            logger.debug(f'Finished job run. Stdout:  {proc.stdout}')
            logger.debug(f'Finished job run. Stderr:  {proc.stderr}')
        else:
            proc = subprocess.Popen(args)

        pid = str(proc.pid)

        logger.info(f"Executor accepted job '{job.run_id}' and assigned identifier '{pid}'")
        return pid

    def _cancel_to_engine(self, job: models.Job) -> bool:
        """
        Kill the job

        TODO Test this! Current mock workflow is very short duration and hard to cancel
        """
        try:
            # WARNING: This DOES NOT VERIFY that PID is the thing originally scheduled. It could be reused.
            #    The subprocess executor is NOT PRODUCTION GRADE and so this is a simplistic implementation.
            os.kill(int(job.executor_id), signal.SIGTERM)
        except OSError as e:
            if e.errno == errno.ESRCH:
                logger.info(f'Failed to kill {job.pk} because it is not running')
                return False
            raise e
        except:
            logger.exception(f'Canceling job {job.pk} failed for unknown reason')
            return False
