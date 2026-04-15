Namespaces
==========

When having a large number of tasks, it's useful to organize them into logical groups.
The best way to do so is to create separate modules for each group of tasks and then import them at the root level.
While we could simply import all tasks from the modules, there is a chance of name conflicts and can create
confusion. To avoid this, we can use namespaces.

The recommended way to define namespaces is with the :func:`quickie.namespace` decorator, which turns a plain
function into a namespace at module level.

.. WARNING::
    A namespace must be assigned to a module-level variable (or nested inside another namespace) to be discovered.
    The task-discovery loop works by inspecting the attributes of the module.

.. NOTE::
    Namespaces are loaded **lazily**: a namespace's function body is not executed until one of its tasks is
    actually needed (e.g. at task lookup or tab completion time).  This means expensive imports inside a
    ``@namespace`` function do not slow down unrelated commands.

Using the ``@namespace`` decorator
-----------------------------------

The :func:`quickie.namespace` decorator replaces a function with a :class:`~quickie.Namespace` instance.
The function may return:

* a **dict** mapping path strings to tasks / sub-modules
* a **list** (or any iterable) of tasks / sub-modules — shorthand for ``{"": [...]}``
* a **single** task or module — shorthand for ``{"": [obj]}``

Quickie only resolves a namespace when one of its task keys is actually requested. This keeps startup
fast even if other namespaces perform expensive imports.

**Bare form** — the function name becomes the path prefix:

.. code-block:: python

    # MyProject/_qk/__init__.py
    from quickie import namespace
    from . import public, test

    @namespace
    def tasks():
        return {
            # Test and public tasks are available at the root.
            # If there are tasks with the same name, those under `public` will be used
            # as it is loaded last, overriding the `test` tasks with the same name.
            "": [test, public],
            # Original public tasks are still available under `tasks:public:`
            "public": [public],
            # Original test tasks are still available under `tasks:test:`
            "test": [test],
        }

**Explicit path** — override the prefix:

.. code-block:: python

    @namespace(path="ci")
    def _():
        return {"check": [lint, test], "build": [build]}

    # tasks available as `ci:check:lint`, `ci:check:test`, `ci:build:build`

You can also customize how nested namespace paths are joined:

.. code-block:: python

    @namespace(path="tools", separator=".")
    def _():
        return {"python": [lint, test]}

    # tasks available as `tools.python:lint`, `tools.python:test`

The custom ``separator`` only affects how namespace path segments are joined to each other.
Task names and aliases continue to use the normal task separator, ``:``.

**Root shorthand** — name the function ``_`` to register tasks at the root without ``path=""``:

.. code-block:: python

    from quickie import namespace
    from . import public, test

    @namespace
    def _():
        return {"": [test, public], "public": [public], "test": [test]}

    # tasks available directly as `<task-name>`, `public:<task-name>`, `test:<task-name>`

This is equivalent to ``@namespace(path="")``.  The name ``_`` signals "no prefix" at a glance and
avoids having to pass ``path=""`` explicitly.

**Empty path (explicit)** — same effect with an explicit ``path=""``:

.. code-block:: python

    from quickie import namespace
    from . import public, test

    @namespace(path="")
    def _():
        return {
            "": [test, public],
            "public": [public],
            "test": [test],
        }

    # tasks available directly as `<task-name>`, `public:<task-name>`, `test:<task-name>`

The function body can contain any Python logic, including **deferred (lazy) imports**.
Because ``@namespace`` functions are not executed until their tasks are needed, you can place
``import`` statements inside the body to avoid loading heavy modules when unrelated commands run:

.. code-block:: python

    # MyProject/_qk/__init__.py
    from quickie import namespace
    from . import public, test

    @namespace(path="")
    def _():
        tasks = {"": [test, public], "public": [public], "test": [test]}
        try:
            from . import private
            # Private tasks override root tasks with the same name and are
            # also available under `private:`
            tasks[""].append(private)
            tasks["private"] = [private]
        except ImportError:
            pass
        return tasks

This lazy behavior also applies when Quickie is discovering tasks for tab completion: only the
namespace relevant to the completion request is resolved.

Namespaces can be nested, allowing for a hierarchical structure:

.. code-block:: python

    # MyProject/_qk/__init__.py
    from quickie import namespace
    from . import module1, module2, module3

    @namespace
    def all_tasks():
        return {
            "a": [module1],
            "b": [module2, module3],
            "c": {
                "": [module1],
                "1": [module2],
            },
        }

Multiple namespaces can also be defined in the same module:

.. code-block:: python

    # MyProject/_qk/__init__.py
    from quickie import namespace
    from . import module1, module2, module3

    @namespace
    def group_a():
        return [module1]

    @namespace
    def group_b():
        return [module2]

    @namespace(path="tools")
    def _tools():
        return [module3]

The ``Namespace`` class
------------------------

For advanced use cases, you can instantiate :class:`quickie.Namespace` directly and mutate it
after construction. This is useful when task membership is determined entirely at import time.

``Namespace`` also accepts a ``factory=...`` parameter for lazy construction, but in most cases
the ``@namespace`` decorator is the clearer and more ergonomic way to use it.

.. code-block:: python

    # MyProject/_qk/__init__.py
    from quickie import Namespace, task

    namespace = Namespace()

    @task
    def hello(name):
        return f"echo 'Hello, {name}!'"

    @task
    def bye(name):
        return f"echo 'Bye, {name}!'"

    # Task will be available as `namespace:hello`
    namespace.add(hello, "namespace")
    # Multiple tasks can be added at once under the same namespace
    namespace.add([hello, bye], "namespace")

Nested :class:`~quickie.Namespace` instances can also be passed directly:

.. code-block:: python

    from quickie import Namespace
    from . import module1, module2, module3

    namespace = Namespace(
        {
            "a": module1,
            "b": {
                "": module2,
                "1": module3,
            },
            "c": Namespace(
                {
                    "": module1,
                    "1": module2,
                }
            ),
        }
    )
