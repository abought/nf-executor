"""
Executor that submits jobs to AWS batch and checks on status
"""
import logging
import botocore.exceptions
import boto3

from .base import AbstractRunner

from nf_executor.api.enums import JobStatus
from nf_executor.nextflow.exceptions import JobStateException, InvalidRunnerException


logger = logging.getLogger(__name__)


def find_first(iterable, predicate=lambda x: False):
    """Find first item in the list that matches the predicate. Return None if no match found."""
    for item in iterable:
        if predicate(item):
            return item
    return None


# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch/client/submit_job.html

class AWSBatchRunner(AbstractRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self._queue is None:
            raise InvalidRunnerException('The AWS Batch runner requires a queue definition')

    def _submit_to_engine(self, callback_url: str, *args, **kwargs) -> str:
        job = self._job

        client = boto3.client('batch')  # Gets credentials (incl STS) via instance IAM role, else hard fail
        result = client.submit_job(
            # Dev note: shows `botocore.errorfactory.ClientException` using nonexistent job definition etc.
            jobName=job.run_id,
            jobDefinition=job.workflow.definition_path,
            jobQueue=self._queue,
            # TODO: identify params required by job and how to pass
            parameters={},
        )
        return result['jobArn']

    def _cancel_to_engine(self) -> bool:
        """Canceling a batch job is tricky, because it depends heavily on the job state. Need to be careful here."""
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch/client/cancel_job.html
        job = self._job

        status = self._check_run_state()
        if job.status in {JobStatus.error, JobStatus.completed}:
            logger.warning(
                'User attempted to cancel a job that has already concluded: Job ID %s in state %s',
                job.run_id,
                status
            )
            return False

        client = boto3.client('batch')  # Gets credentials (incl STS) via instance IAM role, else hard fail
        # Will terminate for running jobs, and cancel for queued jobs (per docs)
        #   https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch/client/terminate_job.html
        result = client.terminate_job(
            jobId=job.executor_id,
            reason='Manually initiated job cancellation',
        )

        # Payload returns a 200 even if the job is already ended.
        status = result['ResponseMetadata']['HTTPStatusCode']
        return status == 200

    def _check_run_state(self) -> JobStatus:
        job = self._job
        arn = job.executor_id

        client = boto3.client('batch')  # Gets credentials (incl STS) via instance IAM role, else hard fail

        try:
            job_status_payload = client.describe_jobs(jobs=[arn])
        except botocore.exceptions.ClientError:
            return JobStatus.unknown

        job_record = find_first(
            # If job doesn't exist, we receive a normal payload with 0 length jobs array
            job_status_payload['jobs'],
            lambda item: item['jobArn'] == arn
        )

        if job_record is None:
            # Batch retains records for ~7 days post execution. Very old jobs may always be unresolvable.
            return JobStatus.unknown

        status = job_record['STATUS']

        # enum ref:
        #   https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch/client/describe_jobs.html
        if status == 'SUCCEEDED':
            return JobStatus.completed
        elif status == 'FAILED':
            return JobStatus.error
        elif status in {'SUBMITTED', 'PENDING', 'RUNNABLE'}:
            return JobStatus.submitted
        elif status in {'STARTING', 'RUNNING'}:
            return JobStatus.started
        else:
            # If the batch integration has changed, this method must hard-fail
            raise JobStateException
