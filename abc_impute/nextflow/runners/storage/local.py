import logging
import os
import shutil

from .base import AbstractJobStorage

logger = logging.getLogger(__name__)


class LocalStorage(AbstractJobStorage):
    """Helpers for content in local storage"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make sure the directory exists before we try to use it. (unlike S3, prefix matters!)
        if not os.path.isdir(self._path):
            os.makedirs(self._path)

    def setup(self):
        wd = self._path
        if not os.path.isdir(wd):
            logger.info(f'Creating working directory: {wd}')
            os.makedirs(wd)

    def read_contents(self, path: str, mode: str = 'r'):
        full = self.relative(path)
        with open(full, mode) as f:
            return f.read()

    def write_contents(self, path: str, content, mode='w'):
        base = os.path.dirname(path)
        os.makedirs(base, exist_ok=True)  # make containing folder first if needed.
        with open(path, mode) as f:
            f.write(content)

    def _delete(self, path):
        if not os.path.exists(path):
            raise IOError(f'The specified file or folder does not exist: {path}')

        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        else:
            raise IOError('Attempted to delete item that is neither a file nor a folder')
