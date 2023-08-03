"""
Pydantic serializers. These often mirror the structure of the SQLAlchemy models,
  but act as whitelists to control read/write of fields
"""
from datetime import datetime

from pydantic import (
    BaseModel,
    Field,
    validator,
)

from nf_executor.api import enums


class BaseFields(BaseModel):
    """Shared fields across all models. ID is excluded, because we never want ID to be writable."""
    created_on: datetime
    updated_on: datetime


#########################
# Workflow definitions. If we continue with FastAPI, in the future we can break out read and write serializers.
class Workflow(BaseFields):
    id: int

    label: str
    description: str
    version: str

    definition_path: str


#############
# A single user initiated workflow run. Receives updates from nextflow status events on start and complete.
class Job(BaseModel):
    """
    A specific user-initiated NF workflow run. From the system perspective, if a user restarts a job, it is a new record
    """
    id: int = Field(description="The unique ID of this run")

    run_name: str = Field(
        description="A human-readable label. Two runs may have the same label, eg if a user initiates restart."
    )
    workflow: int = Field(description="The target workflow")

    status: enums.JobStatus = enums.JobStatus.submitted

    start: int | None
    duration: int | None  # afaict from nf source code, this is ms, unless longer runs output something else

    # Information about processes run by workflow
    succeed_count: int = 0
    retries_count: int = 0

    success: bool = False  # Did the workflow succeed?

    @validator('status', pre=True)
    def validate_status(cls, value):
        """Converts human-readable values to internal int representation"""
        try:
            if isinstance(value, str):
                return enums.JobStatus[value]
            else:
                return value
        except KeyError as e:
            raise ValueError(f"Invalid status {e}. Valid choices are: {[c.name for c in enums.JobStatus]}")

    class Config:
        orm_mode = True


###########################################################################
# A single task or subprocess within a particular workflow execution
class Task(BaseFields):
    id: int = Field(description="The unique ID of this task")

    name: str
    status: enums.JobStatus = enums.TaskStatus.process_submitted
    exit_code: int


