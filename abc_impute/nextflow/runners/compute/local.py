import errno
import logging
import os
import signal
import subprocess

from abc_impute.api import models
from .base import AbstractRunner

from abc_impute.api.enums import JobStatus


logger = logging.getLogger(__name__)


def is_running(pid: int) -> bool:
    """Check if a process is still running (UNIX only). h/t https://stackoverflow.com/a/6940314"""
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID, but we have no way
        # to know that in a portable fashion.
        raise ValueError('invalid PID 0')
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH)
            raise
    else:
        return True


class SubprocessRunner(AbstractRunner):
    """
    Execute jobs in a subprocess worker that continues running on same host, even after the web app stops.
        ONLY used for dev/testing, and even then we should usually use celery.
    """
    CONFIG_KEY = 'LOCAL_RUNNER'

    def _generate_workflow_options(self, job: models.Job, callback_url: str, *args, **kwargs) -> list[str]:
        """Generate the workflow options used by nextflow when running locally."""
        workflow_def = job.workflow.definition_path

        wd = self._work_dir(job.run_id)
        params_fn = self._params_fn(job.run_id)
        trace_fn = self._trace_fn(job.run_id)
        log_fn = self._log_fn(job.run_id)
        report_fn = self._report_fn(job.run_id)

        res = [
            'nextflow',
            '-log', log_fn,
            'run', workflow_def,
            '-params-file', params_fn,
            '-name', job.run_id,
            '-with-trace', trace_fn,
            '-with-weblog', callback_url,
            '-with-report', report_fn,
            '-work-dir', wd,
        ]
        return res

    def _check_run_state(self) -> JobStatus:
        # PID based execution doesn't keep queue or records, so we have only two states (running or not)
        # That's kind of annoying for guessing error states, so this will return "unknown" status and defer
        #   to trace file as source of truth on job status (`_query_remote_state`)
        job = self._job
        pid = int(job.executor_id)

        ok = is_running(pid)
        if ok:
            return JobStatus.started
        else:
            # Can't get exit code by PID after it's done. Return unknown, and let the reconciliation engine check logs
            return JobStatus.unknown

    def _submit_to_engine(self, callback_url: str, *args, **kwargs) -> str:
        """
        Submit a job to the execution engine
        """
        job = self._job
        args = self._generate_workflow_options(job, callback_url, *args, **kwargs)

        logger.debug(f"Submitting job '{job.run_id}' to executor '{self.__class__.__name__}' with options {args}")

        sync = kwargs.get('sync', False)
        if sync:
            # Really really really only use this for debugging: web request shouldn't ever block on a child process
            proc = subprocess.run(args, capture_output=True)
            logger.debug('Finished job run. Stdout: %s',  proc.stdout)
            logger.debug('Finished job run. Stderr: %s', proc.stderr)
        else:
            proc = subprocess.Popen(args)

        pid = str(proc.pid)

        logger.info(f"Executor accepted job '{job.run_id}' and assigned identifier '{pid}'")
        return pid

    def _cancel_to_engine(self) -> bool:
        """
        Kill the job
        """
        job = self._job
        try:
            # WARNING: This DOES NOT VERIFY that PID is the thing originally scheduled. It could be reused.
            #    The subprocess executor is NOT PRODUCTION GRADE and so this is a simplistic implementation.

            # In the event of a gentle sigterm, NF will send a completed event + error report to http
            os.kill(int(job.executor_id), signal.SIGTERM)
        except OSError as e:
            if e.errno == errno.ESRCH:
                logger.info(f'Failed to kill {job.pk} because it is not running')
                return False
            raise e
        except:
            logger.exception(f'Canceling job {job.pk} failed for unknown reason')
            return False

        return True
