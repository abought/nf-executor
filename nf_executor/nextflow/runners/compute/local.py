import errno
import logging
import os
import signal
import subprocess

from .base import AbstractExecutor

from django.utils import timezone

from nf_executor.api import enums, models

logger = logging.getLogger(__name__)


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

    def _params_fn(self, job: models.Job) -> str:
        # Subprocess executor uses a local filesystem, so unlike s3, it matters if prefix doesn't exist.
        logs_dir = job.logs_dir
        if not os.path.isdir(logs_dir):
            os.makedirs(logs_dir)

        return super()._params_fn(job)

    def _submit_to_engine(self, job: models.Job, callback_uri: str, *args, **kwargs) -> str:
        """
        Submit a job to the execution engine

        TODO: Verify that NF runners can upload report/trace files to s3 and no further file handling is needed
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
