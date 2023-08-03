"""
Database models associated with service
"""
from datetime import timedelta
import typing as ty

from sqlalchemy import (
    Column,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    relationship,
)

from src.db.base import Base


class BaseFieldsMixin:
    """Fields common to all models"""
    id = Column(Integer, primary_key=True, index=True)

    created_on = Column(DateTime, default=datetime.utcnow)  # in future use server_default
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Workflow(BaseFieldsMixin, Base):
    """
    Available workflow definitions, including task paths
    TODO: Multiple versions would be represented by multiple entries. Maybe kludgy?
    """
    __tablename__ = "workflows"

    # executor = Column(String, nullable=True)  # TODO: enum (batch, subprocess, slurm, etc)
    definition_path = Column(String, nullable=False)

    label = Column(String, nullable=False)
    description = Column(String, nullable=False)
    version = Column(String, nullable=False)

    jobs: Mapped[ty.List["Job"]] = relationship(back_populates='workflow')


class Job(BaseFieldsMixin, Base):
    """A specific user-initiated workflow run"""
    __tablename__ = "jobs"

    run_name = Column(String, index=True)  # Not unique (a web app might "restart" a job, eg due to downtime)

    # PID, AWS batch ID, etc. Used to manually check if a job completed, in case of message delivery failure.
    executor_id = Column(String)

    status = Column(Integer, index=True)  # serializer is responsible for enforcing enum membership
    success = Column(Boolean)  # Final status report from the nextflow event stream

    # Time and history tracking
    expire_on = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))  # timestamp. Default: 30 days after submission (so it gets cleaned up eventually). When jobs complete, set to 7 days after completion.

    start = Column(DateTime, nullable=True)
    duration = Column(Integer)  # afaict from nf source code, this is ms, unless longer runs output something else

    # Information about processes (tasks) run by workflow
    succeed_count = Column(Integer)
    retries_count = Column(Integer)

    # Related records
    workflow_id = Column(ForeignKey('workflows.id'), index=True)
    workflow = relationship("Workflow", back_populates='jobs')
    tasks: Mapped[ty.List["Task"]] = relationship(back_populates='job')


class Task(BaseFieldsMixin, Base):
    """Record a specific subtask within a particular workflow run"""
    __tablename__ = "tasks"

    name = Column(String, index=True)  # task name as specified by NF
    status = Column(Integer, index=True)  # serializer is responsible for enforcing enum membership
    exit_code = Column(Integer)

    # timestamps, in the TRACE field of records
    submit = Column(DateTime)  # record created when job submitted. Never null.
    start = Column(DateTime, nullable=True)
    complete = Column(DateTime, nullable=True)

    # Relationships
    job = relationship("Job", back_populates='tasks')
    job_id = Column(ForeignKey('jobs.id'), index=True)

    # Data about job execution. This schema will be defined in the future

############
