"""Useful check tasks."""

import enum
import hashlib
import itertools
import json
import pathlib
import typing

from quickie.conditions.base import BaseCondition

__all__ = [
    "BaseCondition",
    "FilesModified",
    "PathsExist",
]


def condition(func: typing.Callable[..., bool]) -> BaseCondition:
    """Decorator to create a condition from a function."""
    return type(func.__name__, (BaseCondition,), {"__call__": func})()


class All(BaseCondition):
    """Check if all conditions are met."""

    def __init__(self, *conditions: BaseCondition):
        """Initialize the check.

        :param conditions: The conditions to check.
        """
        self.conditions = conditions

    @typing.override
    def __call__(self, task, *args, **kwargs):
        return all(condition(task, *args, **kwargs) for condition in self.conditions)


class FilesModified(BaseCondition):
    """Check if files have been not being modified."""

    _params_identifier: str
    """Unique identifier for the parameters."""

    class _KwargsJsonEncoder(json.JSONEncoder):
        """Custom JSON encoder for the kwargs."""

        def default(self, obj):
            if isinstance(obj, (pathlib.PurePath)):
                return str(obj)
            return super().default(obj)

    class Algorithm(enum.StrEnum):
        """Algorithm to use for checking."""

        MD5 = "md5"
        SHA1 = "sha1"
        SHA256 = "sha256"
        TIMESTAMP = "timestamp"

    def __new__(cls, *args, **kwargs):
        """Create a new instance of the class.

        This is needed to make the class hashable.
        """
        # Hash args and kwargs to create a unique key
        key = (args, json.dumps(kwargs, sort_keys=True, cls=cls._KwargsJsonEncoder))
        instance = super().__new__(cls)
        instance.__init__(*args, **kwargs)
        instance._params_identifier = hashlib.md5(str(key).encode()).hexdigest()
        return instance

    def __init__(
        self,
        paths: typing.Sequence[str | pathlib.Path],
        *,
        exclude: typing.Sequence[str | pathlib.Path] = (),
        algorithm: str | Algorithm = Algorithm.TIMESTAMP,
        allow_missing: bool = False,
    ):
        """Initialize the check.

        The algorithm can be one of :class:`FilesModified.Algorithm`.

        :param paths: The files to check.
        :param exclude: The files to exclude from the check.
        :param algorithm: The algorithm to use for checking.
        :param allow_missing: If True, missing files will be treated as if they have not
            been modified.

        :raises ValueError: If the algorithm is not supported.
        :return: True if the files have been modified, False otherwise.
        """
        self.paths = paths
        self.exclude = exclude
        self.algorithm = self.Algorithm(algorithm)
        self.allow_missing = allow_missing

    def get_cache_file_name(self, task):
        """Return the name of the cache file."""
        return f"{task.name}.filesmodified.{self.algorithm.value}.{self._params_identifier}.json"

    def get_cache_file_path(self, task):
        """Return the path of the cache file."""
        from quickie import app

        return app.tmp_path / self.get_cache_file_name(task)

    @typing.override
    def __call__(self, task, *args, **kwargs):
        from quickie import app

        project_path = app.tasks_path.parent
        files = [project_path / pathlib.Path(file) for file in self.paths]
        exclude = {project_path / pathlib.Path(file) for file in self.exclude}

        # hash the name to make it shorter
        cache_path = self.get_cache_file_path(task)

        cache = self._load_cache(cache_path)
        val_getter = getattr(self, f"_get_{self.algorithm.value}")

        all_matches = True
        for file in self._iter_files(files, exclude):
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
            self._write_cache(cache_path, cache)
        return not all_matches

    def _load_cache(self, cache_path: pathlib.Path):
        """Load the cache."""
        try:
            with open(cache_path) as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def _write_cache(self, cache_path: pathlib.Path, cache: dict):
        """Write the cache."""
        # Make sure the directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as file:
            json.dump(cache, file)

    def _iter_files(
        self,
        files: typing.Iterable[pathlib.Path],
        exclude: set[pathlib.Path],
    ) -> typing.Iterator[pathlib.Path]:
        """Iterate over the files."""
        files = iter(files)
        while file := next(files, None):
            if file in exclude:
                continue
            if file.is_dir():
                files = itertools.chain(files, file.iterdir())
            else:
                yield file

    def _get_timestamp(self, file: pathlib.Path):
        """Get the timestamp of the file."""
        return file.stat().st_mtime

    def _get_md5(self, file: pathlib.Path):
        """Get the md5 hash of the file."""
        return hashlib.md5(file.read_bytes()).hexdigest()

    def _get_sha1(self, file: pathlib.Path):
        """Get the sha1 hash of the file."""
        return hashlib.sha1(file.read_bytes()).hexdigest()

    def _get_sha256(self, file: pathlib.Path):
        """Get the sha256 hash of the file."""
        return hashlib.sha256(file.read_bytes()).hexdigest()


class PathsExist(BaseCondition):
    """Check if the given paths exist."""

    def __init__(self, *paths: pathlib.Path | str):
        """Initialize the check.

        :param paths: The paths to check.
        """
        self.paths = paths

    @typing.override
    def __call__(self, task, *args, **kwargs):
        from quickie import app

        paths = (app.tasks_path / pathlib.Path(path) for path in self.paths)
        return all(path.exists() for path in paths)


class FirstRun(BaseCondition):
    """Check if the task is running for the first time.

    Optionally, checks if the task is being run for the first time with the same
    arguments. Checking arguments only works if the arguments are hashable.
    """

    def __init__(self, *, check_args: bool = False):
        """Initialize the check.

        :param check_args: If True, check if the task is being run for the first time
            with the same arguments. Defaults to False. Note that the arguments must be
            hashable.
        """
        self.check_args = check_args
        self.executed = set()

    @typing.override
    def __call__(self, task, *args, **kwargs):
        # Task can be run with different names, and two tasks can have the same name
        # So we need to check against the class.
        # Also, we need to consider the possibility of the condition being shared
        # between different tasks, so we cannot just mark this task as executed.
        # We could add an attribute to the task, but that could bring other problems.
        if self.check_args:
            key = (task.__class__, args, frozenset(kwargs.items()))
        else:
            key = task.__class__
        if key in self.executed:
            return False
        self.executed.add(key)
        return True
