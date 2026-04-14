Task
====

The simplest form of tasks are functions that just run Python code, and the easiest way to define them is by using the :func:`quickie.task` decorator.

.. code-block:: python

    from quickie import task

    @task
    def hello():
        print("Hello, World!")


This will return a :class:`quickie.tasks.Task` instance, equivalent to:

.. code-block:: python

    from quickie import Task

    @task
    class hello(Task):
        def run(self):
            print("Hello, World!")

The rest of the task classes, such as ``Script`` and ``Command`` are built on top of this class, and simply
replace the ``run`` method with a different implementation.

Function based vs Class based tasks
-----------------------------------

Defining tasks as functions is usually simpler and more concise, but defining them as classes allows for more customization and control.

.. _calling-tasks-from-run:

Calling tasks from within run()
--------------------------------

A task's :meth:`~quickie.tasks.Task.__call__` method runs the full lifecycle
(condition → before → run → after → cleanup) and returns whatever ``run()``
returns.  This means you can compose tasks freely from inside another task's
``run()`` method and work with their results directly:

.. code-block:: python

    from quickie import task, Task

    @task
    def fetch():
        return ["item1", "item2"]

    @task
    def transform(items):
        return [item.upper() for item in items]

    class Pipeline(Task):
        def run(self):
            items = fetch()          # calls full lifecycle, returns list
            return transform(items)  # passes result directly

.. note::

    ``before``, ``after``, and ``cleanup`` return values are always discarded.
    They are intended for declarative, fire-and-forget side effects.  When you
    need to pass a result from one task to another, call the dependency
    directly from ``run()`` as shown above, rather than using ``before``/``after``.

Return values
~~~~~~~~~~~~~

Every task type has a defined return contract:

- :class:`~quickie.tasks.Task` — returns whatever ``run()`` returns (any value).
- :class:`~quickie.tasks.Command` / :class:`~quickie.tasks.Script` — returns
  :class:`subprocess.CompletedProcess`.
- :class:`~quickie.tasks.Group` — returns ``list[Any]``, one entry per
  sub-task, **in definition order**.
- :class:`~quickie.tasks.ThreadGroup` — returns ``list[Any]``, one entry per
  sub-task, **in definition order** (not completion order).

When a task's condition fails or :exc:`~quickie.errors.Skip` is raised inside
``run()``, :meth:`~quickie.tasks.Task.__call__` returns ``None``.
