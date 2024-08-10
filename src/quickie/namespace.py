"""Namespaces for tasks."""

import abc
import typing

if typing.TYPE_CHECKING:
    from quickie.tasks import TaskType


class NamespaceABC(abc.ABC):
    """Abstract base class for namespaces."""

    @abc.abstractmethod
    def get_store_ptr(self) -> typing.MutableMapping[str, "TaskType"]:
        """Get the store of tasks."""

    def register[T: TaskType](self, cls: T, name: str) -> T:
        """Register a task class."""
        name = self.namespace_name(name)
        return self._store(cls, name=name)

    def _store[T: TaskType](self, cls: T, *, name: str) -> T:
        """Store a task class."""
        store = self.get_store_ptr()
        store[name] = cls
        return cls

    def namespace_name(self, name: str) -> str:
        """Modify the name of a task."""
        return name

    @abc.abstractmethod
    def get_task_class(self, name: str) -> "TaskType":
        """Get a task class by name."""


# TODO: Use a single namespace class with an optional parent parameter
class RootNamespace(NamespaceABC):
    """Root namespace for tasks."""

    @typing.override
    def __init__(self):
        self._internal_namespace = {}

    @typing.override
    def get_store_ptr(self):
        return self._internal_namespace

    @typing.override
    def get_task_class(self, name: str) -> "TaskType":
        return self._internal_namespace[name]

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

        Args:
            name: The namespace name.
            separator: The separator to use when referring to tasks in the
                namespace.
            parent: The parent namespace.
        """
        self._namespace = name
        self._parent = parent

    @typing.override
    def get_store_ptr(self):
        return self._parent.get_store_ptr()

    @typing.override
    def namespace_name(self, name: str) -> str:
        name = f"{self._namespace}:{name}"
        return self._parent.namespace_name(name)

    @typing.override
    def get_task_class(self, name: str) -> "TaskType":
        """Get a task class by name, relative to the namespace.

        Args:
            name: The name of the task.

        Returns:
            The task class.
        """
        full_name = self.namespace_name(name)
        return self.get_store_ptr()[full_name]
