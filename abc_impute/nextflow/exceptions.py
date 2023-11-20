"""Parsing and handling exceptions"""


class BaseNextflowException(Exception):
    DEFAULT_MESSAGE: str

    def __init__(self, message=None, *args):
        super().__init__(*args)
        self.message = message or self.DEFAULT_MESSAGE

    def __str__(self):
        return str(self.message)


class InvalidRunnerException(BaseNextflowException):
    DEFAULT_MESSAGE = "Runner is missing required configuration options"


class UnknownEventException(BaseNextflowException):
    """
    If we receive an event we don't know how to parse, this may indicate that Nextflow has changed the event schema.
    Even if this is not a fatal error, it should be a major problem
    """
    DEFAULT_MESSAGE = "Unrecognized nextflow trace event type"


class BadJobException(BaseNextflowException):
    DEFAULT_MESSAGE = "Invalid job configuration"


class StaleJobException(BadJobException):
    """Usually a developer error: job is in progress, complete, or canceled."""
    DEFAULT_MESSAGE = "Attempted to run a job with status other than 'submitted'."


class StorageConfigException(BaseNextflowException):
    DEFAULT_MESSAGE = "Storage is improperly configured"


class StorageAccessException(BaseNextflowException):
    DEFAULT_MESSAGE = "Specified file or folder does not exist"


class TaskStateException(BaseNextflowException):
    """
    This error might be raised if the integration with nextflow or runner changes, eg new enum values or payload format
    """
    DEFAULT_MESSAGE = "Cannot identify task state"


class JobStateException(BaseNextflowException):
    """
    This error might be raised if the integration with nextflow or runner changes, eg new enum values or payload format
    """
    DEFAULT_MESSAGE = "Cannot identify job state"
