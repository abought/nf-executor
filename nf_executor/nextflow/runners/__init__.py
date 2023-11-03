import importlib
import sys

from django.conf import settings


from nf_executor.api.models import Job
from .compute.base import AbstractRunner
from .storage.base import AbstractJobStorage


def _get_class_from_string(path: str):
    """h/t: django internals"""
    mp, clp = path.rsplit('.', maxsplit=1)
    if not (mod := sys.modules.get(mp)):
        mod = importlib.import_module(mp)
    return getattr(mod, clp)


def get_runner(job: Job, *args, **kwargs) -> AbstractRunner:
    """Get a compute executor for the designated workflow"""
    storage = get_storage(job.storage_root, *args, **kwargs)
    return _CC(
        job,
        storage,
        *args,
        **kwargs
    )


def get_storage(job_root: str, root=settings.NF_EXECUTOR['STORAGE_ROOT'], *args, **kwargs) -> AbstractJobStorage:
    """
    Get a job storage object using the working directory under the configured storage root

    This is used to access persistent final job storage like logs and trace files: things that may need to be toggled
     between s3 and a filesystem
    """
    return _SC(job_root, *args, root=root, **kwargs)


# Only one compute/storage engine can be used per app. This is determined from config files at startup.
_CC = _get_class_from_string(settings.NF_EXECUTOR['COMPUTE_ENGINE'])
_SC = _get_class_from_string(settings.NF_EXECUTOR['STORAGE_ENGINE'])
