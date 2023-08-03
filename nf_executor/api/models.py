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
    run_id = models.CharField(
        max_length=40, # nf runIDs are 32 chars
        help_text="Unique run ID, eg as specified to nextflow",
        unique=True,
        null=False,
        blank=False,
        default=None,
        db_index=True,
    )
    name = models.CharField(
        max_length=50,
        help_text="Human readable label. May not be unique due to a user job being re-submitted",
        null=False,
        blank=False,
        db_index=True
    )
    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.SET_NULL,
        null=True,
        help_text="The workflow that this job uses",
        db_index=True
    )
    owner = models.CharField(
        max_length=10,
        help_text="eg User ID provided by an external service. Must not be mutable (username or ID, not email)",
        null=True,
        blank=True,
        db_index=True,
    )

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

    # TASK TRACKING FIELDS FROM NEXTFLOW
    start_on = models.DateTimeField(null=True)
    duration = models.IntegerField(
        default=0,
        help_text="Run time of the job. AFAICT from nf source code, this is in ms"
    )

    succeed_count = models.IntegerField(default=0)
    retries_count = models.IntegerField(default=0)

    tracker = FieldTracker()  # Internal: use to track and respond to field changes

    @property
    def success(self):
        """Convenience property (not used directly in DB queries)"""
        return self.status == JobStatus.completed

    def save(self, *args, **kwargs):
        if self.tracker.has_changed('status') and self.status == JobStatus.completed:
            self.expire_on = timezone.now() + timedelta(days=30)

        super().save(*args, **kwargs)


class Task(TimeStampedModel):
    """One individual task execution record from within a particular job"""
    # TODO: How do we deduplicate name/id of tasks in a run? (NF IDs?)
    job = models.ForeignKey(Job,
                               on_delete=models.SET_NULL,
                               null=True,
                               help_text="The job that this task belongs to",
                               db_index=True)
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

