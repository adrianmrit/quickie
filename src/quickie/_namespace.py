"""Namespaces for tasks."""

import abc
import typing

from quickie.errors import TaskNotFoundError

if typing.TYPE_CHECKING:
    from quickie.tasks import TaskType


class NamespaceABC(abc.ABC):
    """Abstract base class for namespaces."""

    @abc.abstractmethod
    def register[T: TaskType](self, cls: T, name: str) -> T:
        """Register a task class."""

    def namespace_name(self, name: str) -> str:
        """Modify the name of a task."""
        return name

    @abc.abstractmethod
    def get_task_class(self, name: str) -> "TaskType":
        """Get a task class by name."""


class RootNamespace(NamespaceABC):
    """Root namespace for tasks."""

    @typing.override
    def __init__(self):
        self._internal_namespace: dict[str, TaskType] = {}

    @typing.override
    def register[T: TaskType](self, cls: T, name: str) -> T:
        self._internal_namespace[name] = cls
        return cls

    @typing.override
    def get_task_class(self, name: str) -> "TaskType":
        try:
            return self._internal_namespace[name]
        except KeyError:
            raise TaskNotFoundError(name)

    def keys(self):
        """Return the keys of the namespace."""
        return self._internal_namespace.keys()

    def values(self):
        """Return the values of the namespace."""
        return self._internal_namespace.values()

    def items(self):
        """Return the items of the namespace."""
        return self._internal_namespace.items()


class Namespace(NamespaceABC):
    """Namespace for tasks.

    Namespaces can be used to group tasks together. They can be used to
    organize tasks by their functionality, or by the project they belong to.

    Namespaces can be nested. For example, the namespace "project" can have
    the namespace "subproject", which can have the task "task1". The task
    can be referred to as "project.subproject.task1".
    """

    def __init__(self, name: str, *, parent: NamespaceABC):
        """Initialize the namespace.

        :param name: The namespace name.
        :param separator: The separator to use when referring to tasks in the
            namespace.
        :param parent: The parent namespace.
        """
        self._namespace = name
        self._parent = parent

    @typing.override
    def namespace_name(self, name: str) -> str:
        return f"{self._namespace}:{name}"

    @typing.override
    def register[T: TaskType](self, cls: T, name: str) -> T:
        full_name = self.namespace_name(name)
        return self._parent.register(cls, full_name)

    @typing.override
    def get_task_class(self, name: str) -> "TaskType":
        full_name = self.namespace_name(name)
        return self._parent.get_task_class(full_name)
