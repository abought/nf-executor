import abc
import logging
import os
from pathlib import Path


from nf_executor.nextflow.exceptions import StorageAccessException


logger = logging.getLogger(__name__)


class AbstractJobStorage(abc.ABC):
    """
    Helper methods for job storage.

    Used so that runners can read and query different storage types, like saving logs to local volume vs s3
      (usually, other temp files will be written to disk. This abstraction has a narrow and specific use case)
    """
    def __init__(self, logs_dir: str, root: str = None):
        self._path = logs_dir
        if root:
            self._path = self.relative(root, logs_dir, check=False)

        self._p = Path(self._path)  # Used for checking paths

    def get_home(self) -> str:
        """Get the home directory for this storage location (root + project specific name)"""
        return self._path

    def relative(self, *args, check=True):
        """
        Get a pathname relative to the storage location. Default implementation works on most providers.

        By default, raises an error if the new path is above the root directory. Simplistic protection
            against directory traversal attacks.
        """
        res = os.path.join(self._path, *args)

        if check and len(args) > 1:
            p = Path(res).resolve()
            if res == self._path or self._p not in p.parents:
                raise StorageAccessException('Relative path must be a child of root')
        return res

    @abc.abstractmethod
    def setup(self):
        """
        Perform any setup required to use this storage location. Eg, ensure that the bucket exists
          and that job working directory has been created.
        """
        raise NotImplementedError

    def delete(self, path: str = None):
        """Delete a file (with common validation)"""
        if path:
            path = self.relative(path)
            logger.info(f'Deleting specified item: {path}')
        else:
            path = self._path
            logger.info(f'Deleting entire storage working directory: {path}')

        return self._delete(path)

    @abc.abstractmethod
    def read_contents(self, path: str, mode: str = 'r'):
        """Return the full content of a small file (eg log file). Not intended for large binary files."""
        raise NotImplementedError

    def write_contents(self, path: str, content, mode='w'):
        """Write a small file, such as a config file, to the specified path"""
        raise NotImplementedError

    ########
    # Private methods
    @abc.abstractmethod
    def _delete(self, path):
        """Internal implementation per storage subclass"""
        raise NotImplementedError
