"""Useful check tasks."""

import enum
import hashlib
import itertools
import json
import pathlib
import typing

from quickie.utils.conditions.base import BaseCondition

__all__ = [
    "BaseCondition",
    "FilesNotModified",
    "PathsExist",
]

if typing.TYPE_CHECKING:
    from quickie.tasks import TaskType
else:
    type TaskType = typing.Any


def condition(func):
    """Decorator to create a condition from a function."""
    return type(func.__name__, (BaseCondition,), {"__call__": func})()


class FilesNotModified(BaseCondition):
    """Check if files have been not being modified."""

    class Algorithm(enum.Enum):
        """Algorithm to use for checking."""

        MD5 = "md5"
        SHA1 = "sha1"
        SHA256 = "sha256"
        TIMESTAMP = "timestamp"

    def __init__(
        self,
        *files: str | pathlib.Path,
        algorithm: str | Algorithm = Algorithm.TIMESTAMP,
        allow_missing: bool = False,
    ):
        """Initialize the check.

        Args:
            files: The files to check.
            algorithm: The algorithm to use for checking.
            allow_missing: If True, missing files will be treated as if they have not
                been modified.
        """
        self.files = files
        self.algorithm = self.Algorithm(algorithm)
        self.allow_missing = allow_missing

    @typing.override
    def __call__(self, task: TaskType, *args, **kwargs):
        tasks_module_path = task.context.config.TASKS_MODULE_PATH
        files = [tasks_module_path / pathlib.Path(file) for file in self.files]
        # This way the file does not clash with other cache files, and can even be
        # reused by other tasks with the same files and algorithm.
        string = "\n".join(str(f) for f in files)
        # hash the name to make it shorter
        hash = hashlib.md5(string.encode()).hexdigest()
        cache_path = (
            task.context.config.TMP_PATH
            / f"{task.name}.files_not_modified.{self.algorithm}.{hash}.json"
        )

        cache = self.load_cache(cache_path)
        val_getter = getattr(self, f"get_{self.algorithm.value}")

        all_matches = True
        for file in self.iter_files(files):
            key = str(file)
            if not file.exists():
                # Remove file from cache if it no longer exists
                # In future runs if it comes to existence, it
                # should be treated as if it changed.
                cache.pop(key, None)
                if not self.allow_missing:
                    all_matches = False
            else:
                val = val_getter(file)
                matches = cache.get(key, None) == val
                if not matches:
                    cache[key] = val
                    all_matches = False

        if not all_matches:
            self.write_cache(cache_path, cache)
        return all_matches

    def load_cache(self, cache_path: pathlib.Path):
        """Load the cache."""
        try:
            with open(cache_path) as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def write_cache(self, cache_path: pathlib.Path, cache: dict):
        """Write the cache."""
        with open(cache_path, "w") as file:
            json.dump(cache, file)

    def iter_files(
        self, files: typing.Iterator[pathlib.Path]
    ) -> typing.Iterator[pathlib.Path]:
        """Iterate over the files."""
        for file in files:
            if file.is_dir():
                files = itertools.chain(files, file.iterdir())
            else:
                yield file

    def get_timestamp(self, file: pathlib.Path):
        """Get the timestamp of the file."""
        return file.stat().st_mtime

    def get_md5(self, file: pathlib.Path):
        """Get the md5 hash of the file."""
        return hashlib.md5(file.read_bytes()).hexdigest()

    def get_sha1(self, file: pathlib.Path):
        """Get the sha1 hash of the file."""
        return hashlib.sha1(file.read_bytes()).hexdigest()

    def get_sha256(self, file: pathlib.Path):
        """Get the sha256 hash of the file."""
        return hashlib.sha256(file.read_bytes()).hexdigest()


class PathsExist(BaseCondition):
    """Check if the given paths exist."""

    def __init__(self, *paths: pathlib.Path | str):
        """Initialize the check.

        Args:
            paths: The paths to check.
        """
        self.paths = paths

    @typing.override
    def __call__(self, task: TaskType, *args, **kwargs):
        tasks_module_path = task.context.config.TASKS_MODULE_PATH
        paths = (tasks_module_path / pathlib.Path(path) for path in self.paths)
        return all(path.exists() for path in paths)
