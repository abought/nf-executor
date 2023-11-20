"""
Executor that submits jobs to AWS batch and checks on status
"""
import logging
import botocore.exceptions
import boto3

from .base import AbstractRunner

from abc_impute.api.enums import JobStatus
from abc_impute.nextflow.exceptions import JobStateException, InvalidRunnerException


logger = logging.getLogger(__name__)


def find_first(iterable, predicate=lambda x: False):
    """Find first item in the list that matches the predicate. Return None if no match found."""
    for item in iterable:
        if predicate(item):
            return item
    return None


# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/batch/client/submit_job.html

class AWSBatchRunner(AbstractRunner):
    """
    Run a workflow in AWS Batch

    NOTE: At present, this is heavily hard coded to use nextflow with one particular custom
        Docker container + AWS Batch command.
        It provides specific hard coded envvars (for entrypoint script) and command args (for batch job definition).

        We can make this more modular/configurable in the future
    """
    CONFIG_KEY = 'AWS_BATCH_RUNNER'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The AWS batch queue to use for all worflow-coordination jobs. Individual workflows must specify the queues
        #   for their own tasks; WF runner only controls the nextflow process itself.
        self._head_queue_arn = self._config['HEAD_QUEUE_ARN']

        # The AWS batch job definition that defines how to run nextflow. (using a special container def for this project)
        self._head_def_arn = self._config['HEAD_DEF_ARN']

    def _submit_to_engine(self, callback_url: str, *args, **kwargs) -> str:
        """
        Submit workflow to engine: run the nextflow process as an AWS batch job that in turn spawns other batch jobs.
         Because of limitations in nextflow, this is tightly coupled to a specific custom dockerfile that wraps
          Nextflow and adds missing features like storing log and workflow defs on s3
        """
        job = self._job

        workflow_path = job.workflow.definition_path
        if not workflow_path.startswith('arn'):
            raise InvalidRunnerException(f'The specified workflow {job.workflow.pk} must be an AWS Batch job definition ARN')

        env = [
                {"name": "NF_CONFIG", "value": job.workflow.definition_config},
                {"name": "NF_LOGS_DEST", "value": self._log_fn(job.run_id)},
            ]
        if job.workflow.definition_path.startswith('s3'):
            env.append({"name": "NF_WORKFLOW_S3_PATH", "value": job.workflow.definition_path})

        runner_def_params = {
            # NF options
            "WorkflowPath": 'downloaded_workflow/' if workflow_path.startswith('s3') else workflow_path,
            "TraceLogFile": self._trace_fn(job.run_id),
            "ReportHTMLFile": self._report_fn(job.run_id),
            "ConfigFile": ".nextflow/config",  # Our container dumps envvar text to this file inside container
            "BucketDir": self._work_dir(job.run_id),
            # WF options
            "ParamsFile": self._params_fn(job.run_id),
        }
        client = boto3.client('batch')  # Gets credentials (incl STS) via instance IAM role, else hard fail
        result = client.submit_job(
            # Dev note: shows `botocore.errorfactory.ClientException` using nonexistent job definition etc.
            jobName=job.run_id,
            jobDefinition=self._head_def_arn,
            jobQueue=self._head_queue_arn,
            parameters=runner_def_params,
            containerOverrides={
                'environment': env
            },
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

        status = job_record['status']

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
