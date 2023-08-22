import importlib
import sys
import typing as ty

from django.conf import settings


from nf_executor.api.models import Workflow
from .compute.base import AbstractExecutor
from .storage.base import AbstractJobStorage


def _get_class_from_string(path: str):
    mp, clp = path.rsplit('.', maxsplit=1)
    if not (mod := sys.modules.get(mp)):
        mod = importlib.import_module(mp)
    return getattr(mod, clp)


def get_executor(storage, *args, **kwargs) -> AbstractExecutor:
    """Get a compute executor for the designated workflow"""
    return _CC(storage, *args, **kwargs)


def get_storage(logs_dir: str, root=settings.NF_EXECUTOR['logs_dir'], *args, **kwargs) -> AbstractJobStorage:
    """
    Get a job storage object using the working directory under the configured storage root

    This is used to access persistent final job storage like logs and trace files: things that may need to be toggle
     between s3 and a filesystem
    """
    return _SC(logs_dir, *args, root=root, **kwargs)


_CC = _get_class_from_string(settings.NF_EXECUTOR['compute'])
_SC = _get_class_from_string(settings.NF_EXECUTOR['storage'])