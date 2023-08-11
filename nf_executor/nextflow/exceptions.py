"""Parsing and handling exceptions"""


class BaseNextflowException(Exception):
    DEFAULT_MESSAGE: str

    def __init__(self, message=None, *args):
        super().__init__(*args)
        self.message = message or self.DEFAULT_MESSAGE

    def __str__(self):
        return str(self.message)


class UnknownEventException(BaseNextflowException):
    """
    If we receive an event we don't know how to parse, this may indicate that Nextflow has changed the event schema.
    Even if this is not a fatal error, it should be a major problem
    """
    DEFAULT_MESSAGE = "Unrecognized nextflow trace event type"


class StaleJobException(BaseNextflowException):
    """Usually a developer error: job is in progress, complete, or canceled."""
    DEFAULT_MESSAGE = "Attempted to run a job with status other than 'submitted'."
