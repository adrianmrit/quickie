"""Namespaces for tasks."""

import typing

import collections.abc

from quickie.errors import TaskNotFoundError

if typing.TYPE_CHECKING:
    from quickie.tasks import Task


DEFAULT_SEPARATOR = ":"


def is_task_instance(obj) -> typing.TypeGuard["Task"]:
    from quickie.tasks import Task

    return isinstance(obj, Task)


def _merge_aliases(root: str, aliases: typing.Sequence[str]) -> typing.Sequence[str]:
    if not root:
        return aliases
    if not aliases:
        return [root]
    return [
        DEFAULT_SEPARATOR.join([root, alias]) if alias else root for alias in aliases
    ]


def _merge_alias(root: str, alias: str) -> str:
    if not root:
        return alias
    if not alias:
        return root
    return DEFAULT_SEPARATOR.join([root, alias])


class RootNamespace(collections.abc.Mapping[str, "Task"]):
    """Root namespace for tasks.

    This class is used to store tasks with their full mappings. This should
    not be used directly, instead use the :class:`Namespace` class.
    """

    def __init__(self):
        self._mappings: dict[str, "Task"] = {}

    def __getitem__(self, key):
        try:
            return self._mappings[key]
        except KeyError:
            raise TaskNotFoundError(key)

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._mappings)

    def __len__(self) -> int:
        return len(self._mappings)

    def register(self, obj: "Task", *, namespace: str | typing.Sequence[str] = ""):
        """Register an object to a namespace.

        :param module: The object to register.
        :param namespace: The namespace or namespaces to register the obj under.
        """
        if isinstance(namespace, str):
            namespace = [namespace]

        for k in namespace:
            self._mappings[k] = obj

    def load(self, obj):
        """Load tasks from an object, usually a module.

        :param obj: The object to load tasks from.
        """
        # Assume obj is a module
        current: None | typing.Iterator[tuple[str, typing.Any]] = iter(
            ("", obj)
            for obj in obj.__dict__.values()
            if is_task_instance(obj) or isinstance(obj, Namespace)
        )
        stack = []

        # We use in-order traversal to load the tasks.
        # This allows us to load the tasks in the order they appear in the module,
        # with tasks loaded later overriding tasks loaded earlier.
        # We also allow tasks to be loaded from nested namespaces, traversing the
        # subtrees as they appear.
        #
        # Example:
        #   module
        #   ├── task1
        #   ├── namespace1
        #   │   ├── task2
        #   │   └── namespace2
        #   │       └── task3
        #   |   └── task4
        #   └── task5
        #
        # The tasks will be loaded in the order: task1, task2, task3, task4, task5
        while current is not None or stack:
            while current is not None:
                try:
                    current_path, value = next(current)
                except StopIteration:
                    current = None
                else:
                    if current in stack:
                        if current_path:
                            raise ValueError(
                                "Circular reference detected when loading tasks for namespace: "
                                + current_path
                            )
                        else:
                            raise ValueError(
                                "Circular reference detected when loading tasks for the root namespace."
                            )
                    stack.append(current)
                    if isinstance(value, list):
                        # Treat lists as subtrees and load them next
                        current = iter((current_path, v) for v in value)
                    elif is_task_instance(value) and not value.private:
                        paths = _merge_aliases(
                            current_path, (value.name, *value.aliases)
                        )
                        for p in paths:
                            self.register(value, namespace=p)
                        current = None
                    elif isinstance(value, Namespace):
                        current = iter(value.items())
                    elif isinstance(value, collections.abc.Mapping):
                        value = Namespace(value, path=current_path)
                        current = iter(value.items())
                    elif hasattr(value, "__dict__"):
                        current = iter(
                            (current_path, v)
                            for v in value.__dict__.values()
                            if is_task_instance(v) or isinstance(v, Namespace)
                        )
                    else:
                        # Should not happen, but just in case
                        raise ValueError("Invalid object.")
            if stack:
                current = stack.pop()


class Namespace:
    """Used to group modules."""

    def __init__(
        self, mapping=None, path: str = "", separator: str = DEFAULT_SEPARATOR
    ):
        self._mappings: dict[str, list] = {}
        self.path = path
        self.separator = separator

        if mapping is not None:
            self.update(mapping)

    def add(self, obj: object, path):
        """Register an object to a namespace.

        :param module: The object to register.
        :param namespace: The namespace or namespaces to register the obj under.
        """
        # if is_task_cls(obj):
        #     raise ValueError("Task classes cannot be registered directly.")
        if not isinstance(obj, collections.abc.Sequence):
            obj = [obj]
        path = _merge_alias(self.path, path)
        self._mappings.setdefault(path, []).extend(obj)

    def update(self, mapping: dict):
        for k, v in mapping.items():
            self.add(v, path=k)

    def items(self):
        return self._mappings.items()
