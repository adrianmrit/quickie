"""Namespaces for tasks."""

import typing

import collections.abc

from quickie.errors import CircularDependencyError, TaskNotFoundError

if typing.TYPE_CHECKING:
    from quickie.tasks import Task


DEFAULT_SEPARATOR = ":"

_NamespaceFactory = typing.Callable[[], typing.Any]


def is_task_instance(obj) -> typing.TypeGuard["Task"]:
    from quickie.tasks import Task

    return isinstance(obj, Task)


def _merge_aliases(
    root: str,
    aliases: typing.Sequence[str],
    separator: str = DEFAULT_SEPARATOR,
) -> typing.Sequence[str]:
    if not root:
        return aliases
    if not aliases:
        return [root]
    return [separator.join([root, alias]) if alias else root for alias in aliases]


def _merge_alias(root: str, alias: str, separator: str = DEFAULT_SEPARATOR) -> str:
    if not root:
        return alias
    if not alias:
        return root
    return separator.join([root, alias])


class RootNamespace(collections.abc.Mapping[str, "Task"]):
    """Root namespace for tasks.

    This class is used to store tasks with their full mappings. This should
    not be used directly, instead use the :class:`quickie.Namespace` class.

    Namespaces discovered during :meth:`load` are stored in ``_pending`` and
    resolved on demand: requesting a task key resolves only the namespaces
    whose path is a prefix of that key.  Iteration and length resolve all
    pending namespaces first.
    """

    def __init__(self):
        self._mappings: dict[str, "Task"] = {}
        self._pending: dict[str, list["Namespace"]] = {}
        self._resolving: set[int] = set()  # ids of namespaces currently being resolved

    # ------------------------------------------------------------------
    # Mapping protocol
    # ------------------------------------------------------------------

    def __getitem__(self, key: str) -> "Task":
        if key in self._mappings:
            return self._mappings[key]
        if self._pending:
            self._resolve_for_key(key)
        if key in self._mappings:
            return self._mappings[key]
        raise TaskNotFoundError(key, candidates=list(self._mappings))

    def __iter__(self) -> typing.Iterator[str]:
        self._resolve_all()
        return iter(self._mappings)

    def __len__(self) -> int:
        self._resolve_all()
        return len(self._mappings)

    def __contains__(self, key: object) -> bool:
        if key in self._mappings:
            return True
        if self._pending and isinstance(key, str):
            self._resolve_for_key(key)
        return key in self._mappings

    # ------------------------------------------------------------------
    # Registration and loading
    # ------------------------------------------------------------------

    def register(self, obj: "Task", *, namespace: str | typing.Sequence[str] = ""):
        """Register a task under one or more keys.

        :param obj: The task to register.
        :param namespace: The key or keys to register the task under.
        """
        if isinstance(namespace, str):
            namespace = [namespace]
        for k in namespace:
            self._mappings[k] = obj

    def _register_task(self, path: str, task: "Task") -> None:
        if not task.private:
            for p in _merge_aliases(path, (task.name, *task.aliases)):
                self.register(task, namespace=p)

    def _defer_namespace(self, ns: "Namespace") -> None:
        if id(ns) in self._resolving:
            raise CircularDependencyError(ns.path)
        self._pending.setdefault(ns.path, []).append(ns)

    def _scan_obj(self, obj, path: str) -> None:
        """Register tasks and defer namespaces found directly on *obj.__dict__*."""
        for v in obj.__dict__.values():
            if is_task_instance(v):
                self._register_task(path, v)
            elif isinstance(v, Namespace):
                self._defer_namespace(v)

    def load(self, obj):
        """Shallow-load tasks from an object (usually a module).

        :class:`Task` instances found directly on the object are registered
        immediately.  :class:`Namespace` instances are stored in
        ``_pending`` and resolved on demand.
        """
        self._scan_obj(obj, "")

    def _process_items(self, path: str, items: list, seen_lists: set[int]) -> None:
        """Register tasks and defer sub-namespaces found in *items* at *path*.

        *seen_lists* tracks visited list ids along the current traversal path
        for cycle detection; pass a fresh ``set()`` for each top-level call.
        """
        list_id = id(items)
        if list_id in seen_lists:
            raise CircularDependencyError(path)
        seen_lists.add(list_id)
        try:
            for obj in items:
                if is_task_instance(obj):
                    self._register_task(path, obj)
                elif isinstance(obj, Namespace):
                    self._defer_namespace(obj)
                elif isinstance(obj, collections.abc.Mapping):
                    self._defer_namespace(Namespace(mapping=obj, path=path))
                elif isinstance(obj, list):
                    self._process_items(path, obj, seen_lists)
                elif hasattr(obj, "__dict__"):
                    self._scan_obj(obj, path)
        finally:
            seen_lists.discard(list_id)

    def _resolve_one(self, ns: "Namespace") -> None:
        """Traverse one :class:`Namespace` and register its tasks.

        Sub-namespaces found during traversal are stored back into
        ``_pending`` rather than being recursed into immediately.
        """
        ns_id = id(ns)
        if ns_id in self._resolving:
            raise CircularDependencyError(ns.path)
        self._resolving.add(ns_id)
        try:
            for path, obj_list in ns.items():
                self._process_items(path, obj_list, set())
        finally:
            self._resolving.discard(ns_id)

    def _resolve_for_key(self, key: str) -> None:
        """Resolve pending namespaces whose path is a prefix of *key*.

        Falls back to resolving everything if the key still isn't found, so
        that :meth:`__getitem__` can build "did you mean?" candidates.
        """
        parts = key.split(DEFAULT_SEPARATOR)
        for i in range(len(parts) + 1):
            prefix = DEFAULT_SEPARATOR.join(parts[:i])
            if prefix in self._pending:
                self._resolve_pending(prefix)
                if key in self._mappings:
                    return
        self._resolve_all()

    def _resolve_pending(self, path: str) -> None:
        """Resolve all pending namespaces registered under *path*."""
        for ns in self._pending.pop(path, []):
            self._resolve_one(ns)

    def _resolve_all(self) -> None:
        """Resolve all remaining pending namespaces."""
        while self._pending:
            path = next(iter(self._pending))
            self._resolve_pending(path)


class Namespace:
    """Used to group tasks and modules under a shared path prefix.

    A :class:`Namespace` can be populated eagerly (via *mapping* or :meth:`add`)
    or lazily (via *factory*).  When a *factory* is provided the function is
    not called until the first time :meth:`items` is accessed, which lets you
    defer expensive imports:

    .. code-block:: python

        @namespace
        def ci():
            from . import heavy  # imported only when ci tasks are needed
            return [heavy]

    The factory may return:

    * a **dict** mapping path strings to tasks/modules/iterables
    * a **list** (or any iterable) of tasks/modules — shorthand for ``{"": [...]}``
    * a **single** task or module — shorthand for ``{"": [obj]}``

    Pass *mapping* **or** *factory*, not both.
    """

    def __init__(
        self,
        mapping=None,
        path: str = "",
        separator: str = DEFAULT_SEPARATOR,
        factory: "_NamespaceFactory | None" = None,
    ):
        if mapping is not None and factory is not None:
            raise ValueError("Pass 'mapping' or 'factory', not both.")

        self._mappings: dict[str, list] = {}
        self.path = path
        self.separator = separator
        self._factory = factory
        self._resolved = factory is None

        if mapping is not None:
            self.update(mapping)

    # ------------------------------------------------------------------
    # Lazy resolution
    # ------------------------------------------------------------------

    def _resolve(self) -> None:
        """Call the factory and populate ``_mappings`` (once)."""
        if self._resolved:
            return
        result = self._factory()  # type: ignore[misc]
        if not isinstance(result, collections.abc.Mapping):
            if isinstance(result, collections.abc.Iterable) and not isinstance(
                result, (str, bytes)
            ):
                result = {"": list(result)}
            else:
                result = {"": [result]}
        self.update(result)
        self._resolved = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, obj: object, path: str = ""):
        """Add an object (task, module, or list thereof) under a path.

        :param obj: The object to register.
        :param path: The sub-path relative to this namespace's :attr:`path`.
            Defaults to ``""`` (merge into the namespace root).
        """
        if not isinstance(obj, collections.abc.Sequence):
            obj = [obj]
        full_path = _merge_alias(self.path, path, self.separator)
        self._mappings.setdefault(full_path, []).extend(obj)

    def update(self, mapping: "collections.abc.Mapping"):
        """Add all entries from *mapping* into this namespace.

        :param mapping: A mapping of ``{path: obj}`` pairs passed to :meth:`add`.
        """
        for k, v in mapping.items():
            self.add(v, path=k)

    def items(self):
        """Return the internal ``(full_path, objects)`` pairs, resolving lazily."""
        self._resolve()
        return self._mappings.items()


# ---------------------------------------------------------------------------
# @namespace decorator
# ---------------------------------------------------------------------------

_NamespaceFunc = _NamespaceFactory


@typing.overload
def namespace(obj: _NamespaceFunc) -> Namespace: ...


@typing.overload
def namespace(
    *,
    path: "str | None" = None,
    separator: str = DEFAULT_SEPARATOR,
) -> "typing.Callable[[_NamespaceFunc], Namespace]": ...


def namespace(  # type: ignore[misc]
    obj: "_NamespaceFunc | None" = None,
    *,
    path: "str | None" = None,
    separator: str = DEFAULT_SEPARATOR,
) -> "Namespace | typing.Callable[[_NamespaceFunc], Namespace]":
    """Decorator that turns a function into a lazy :class:`Namespace` instance.

    The decorated function is replaced by a :class:`Namespace` at module level,
    so the normal task-discovery loop picks it up without any extra wiring.
    The function body is **not called until the namespace's tasks are actually
    needed**, allowing expensive imports to be deferred:

    .. code-block:: python

        @namespace
        def ci():
            from . import heavy   # only imported when ci tasks are requested
            return [heavy]

    The function may return:

    * a **dict** mapping path strings to tasks/modules/iterables
    * a **list** (or any iterable) of tasks/modules — shorthand for ``{"": [...]}``
    * a **single** task or module — shorthand for ``{"": [obj]}``

    A function named ``_`` automatically uses an empty path (root namespace),
    so ``@namespace def _(): ...`` is the idiomatic way to register tasks at
    the root without a prefix.

    Usage:

    .. code-block:: python

        from quickie import namespace, task

        @task
        def build(): ...

        @task
        def test(): ...

        # Bare form — function name becomes the path prefix
        @namespace
        def tools():
            return [build, test]

        # Parametrised form — explicit path and/or separator
        @namespace(path="ci", separator=":")
        def ci_tasks():
            return {"": [build], "check": [test]}

        # Root namespace — use _ as the function name (no prefix)
        @namespace
        def _():
            return {"": [build, test], "build": [build], "test": [test]}

        # Equivalent explicit form
        @namespace(path="")
        def root_extras():
            return [build]

    :param obj: The function to decorate (used in the bare ``@namespace`` form).
    :param path: Override the path prefix.  Defaults to the function name;
        functions named ``_`` default to ``""`` (root).
    :param separator: Separator used to join path segments.
        Defaults to :data:`DEFAULT_SEPARATOR` (``":"``).
    :returns: A :class:`Namespace` instance (lazy: the function is not called
        until its tasks are first accessed).
    """

    def decorator(fn: _NamespaceFunc) -> Namespace:
        if path is None:
            resolved_path = "" if fn.__name__ == "_" else fn.__name__
        else:
            resolved_path = path
        return Namespace(path=resolved_path, separator=separator, factory=fn)

    if obj is not None:
        return decorator(obj)
    return decorator
