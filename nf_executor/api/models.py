from datetime import timedelta

from django.db import models
from django.utils import timezone

from .enums import (JobStatus, TaskStatus)

from model_utils import FieldTracker
from model_utils.models import TimeStampedModel


class Workflow(TimeStampedModel):
    """A workflow (NF or other) that can be used to create jobs"""
    name = models.CharField(
        max_length=50,
        null=False,
        blank=False,
        db_index=True,
    )
    description = models.CharField(
        max_length=100,
        help_text="Human readable description of workflow"
    )
    version = models.CharField(
        max_length=10,
        help_text="Workflow version",
        null=False,
        blank=False
    )

    # executor  ## TODO: in future, some sort of plugin system for allowed executors (batch, subprocess, etc)

    definition_path = models.CharField(
        max_length=256,
        help_text="Depends on executor type. Folder location, container ARN, etc.",
    )

    def __str__(self):
        return f"{self.name} (v{self.version})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'version'],
                name='Name + version'
            )
        ]


def future_date(days=30):
    return timezone.now() + timedelta(days=days)


class Job(TimeStampedModel):
    """One specific execution of a given workflow. Restart/resubmits are tracked as a separate execution."""

    #####
    # Fields set at model creation
    run_id = models.CharField(
        max_length=40,  # nf runIDs are 32 chars
        help_text="Unique-per-workflow run ID provided to the executor. If a job is restarted, specify a new ID.",
        null=False,
        blank=False,
        default=None,
        db_index=True,
    )
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.SET_NULL,
        null=True,
        help_text="The workflow that this job uses",
        db_index=True
    )
    params = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text="User-specified params unique to this workflow"
    )
    workdir = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        help_text="Working directory where job specific files are stored. Managed by executor, not user."
                  " TODO: special outputs, like NF trace files, should be accessible after job completes too."
    )
    owner = models.CharField(
        max_length=100,
        help_text="eg User ID provided by an external service. Must not be mutable (username or ID, not email)",
        null=True,
        blank=True,
        db_index=True,
    )

    #######
    # Fields managed internally by executor service
    executor_id = models.CharField(
        max_length=50,
        help_text="Used to manually check job status (in case of message delivery failure). PID, AWS Batch arn, etc",
    )

    status = models.IntegerField(choices=JobStatus.choices(), default=JobStatus.submitted)

    # Time and history tracking. Submission is tracked by TSM `created` field automatically
    expire_on = models.DateTimeField(
        default=future_date,
        help_text="30 days after submission OR 7 days after completion"
    )

    # TASK TRACKING FIELDS FROM NEXTFLOW (note: `created` and `modified` fields exist in TimeStampedModel)
    started_on = models.DateTimeField(null=True)
    completed_on = models.DateTimeField(null=True)
    duration = models.IntegerField(
        default=0,
        help_text="Run time of the job. AFAICT from nf source code, this is in ms"
    )

    succeed_count = models.IntegerField(default=0)
    retries_count = models.IntegerField(default=0)

    tracker = FieldTracker()  # Internal: use to track and respond to field changes

    def save(self, *args, **kwargs):
        if self.tracker.has_changed('status') and self.status == JobStatus.completed:
            self.expire_on = timezone.now() + timedelta(days=30)

        super().save(*args, **kwargs)

    class Meta:
        # The run ID can only be used once per workflow type.
        constraints = [
            models.UniqueConstraint(
                fields=['run_id', 'workflow'],
                name='IDs are unique per workflow'
            )
        ]


class Task(TimeStampedModel):
    """One individual task execution record from within a particular job"""
    # TODO: How do we deduplicate name/id of tasks in a run? (NF IDs?)
    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True,
        help_text="The job that this task belongs to",
        db_index=True
    )
    task_id = models.CharField(
        max_length=10,
        help_text="ID used to link two event records for the same event, eg nextflow trace `task_id`"
    )
    native_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="ID used by the underlying execution system. Allows debugging of dropped tasks, eg aws batch"
    )

    name = models.CharField(
        max_length=50,
        help_text="Task name as specified by NF",
    )

    status = models.IntegerField(choices=TaskStatus.choices(), default=TaskStatus.process_submitted)
    exit_code = models.IntegerField(null=True, help_text="Exit code of the process (once completed)")

    # Timestamps, in the TRACE field of records
    submitted_on = models.DateTimeField(
        null=True,
        help_text="Submit time from TRACE field of records"
    )
    started_on = models.DateTimeField(
        null=True,
        help_text="Run start time from TRACE field of records"
    )
    completed_on = models.DateTimeField(
        null=True,
        help_text="Run complete time from TRACE field of records"
    )

    class Meta:
        # The same task ID can only be used once per job.
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'task_id'],
                name='Task per job'
            )
        ]
