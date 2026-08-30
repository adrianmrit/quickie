Watch Mode
==========

Watch mode re-runs a task automatically whenever files change.  This is useful
for development workflows like linting, testing, or building where you want
immediate feedback after saving a file.

Quick Start
-----------

.. code-block:: bash

   qk --watch my-task

The task runs immediately, then watches for file changes and re-runs whenever a
change is detected.  Press ``Ctrl+C`` to stop.

CLI Options
-----------

``-w`` / ``--watch``
   Enable watch mode.  Requires a task name.

``--watch-paths PATH``
   Directory paths to watch.  Repeatable.  Values are not split on ``;``.
   Paths resolve relative to the task's effective working directory.  Defaults
   to that directory.

   .. code-block:: bash

      qk --watch --watch-paths src --watch-paths lib my-task

``--watch-ignore-paths PATH``
   Directory paths to ignore.  Repeatable.  Values are not split on ``;``.

``--watch-patterns PATTERN``
   Patterns for changed files.  Repeatable.  Patterns in one value may be
   separated with ``;``, matching ``watchmedo log``.  Use watchdog wildcard
   syntax such as ``**/*.py`` for nested paths.

``--watch-ignore-patterns PATTERN``
   Patterns for changed files to ignore.  Repeatable.  Patterns in one value
   may be separated with ``;``.

``--watch-recursive``
   Watch directories recursively.  Disabled by default, matching
   ``watchmedo log``.

``--watch-debounce SECS``
   Seconds to wait after a change before re-running (default: ``0.5``).
   Prevents rapid re-runs when an IDE auto-formats multiple files on save.

   .. code-block:: bash

      qk --watch --watch-debounce 1.0 my-task

How It Works
------------

Quickie uses `watchdog <https://pypi.org/project/watchdog/>`_ for OS-native file
watching:

- **macOS**: FSEvents (efficient, low overhead)
- **Linux**: inotify
- **Windows**: ReadDirectoryChangesW

The observer runs in a background thread.  When a file change is detected, a
debounce timer starts.  If no further changes occur within the debounce window,
the task is re-run.  This prevents rapid re-runs during multi-file saves.

Declarative Watch Configuration
--------------------------------

Instead of passing the watch options on every
invocation, you can declare them directly on the task.  When ``qk --watch``
is used, the CLI picks up these defaults automatically.

**Using the ``@task`` decorator:**

.. code-block:: python

   from quickie import task

   @task(
       watch_paths=["src/"],
       watch_ignore_paths=["vendor/"],
       watch_patterns=["*.py"],
       watch_ignore_patterns=["*_generated.py", "*.pyc"],
       watch_debounce=1.0,
   )
   def lint():
       """Run linter on source files."""
       return ["ruff", "check", "src/"]

Then just run:

.. code-block:: bash

   qk --watch lint

**Using a task class:**

.. code-block:: python

   from quickie import tasks

   class LintTask(tasks.Command):
       watch_paths = ["src/"]
       watch_ignore_paths = ["tests/"]

       def get_cmd_args(self):
           return ["ruff", "check", "src/"]

Available watch attributes (used as defaults when ``--watch`` is passed):

- ``watch_paths`` — Directories to watch.
- ``watch_ignore_paths`` — Directory paths to ignore.
- ``watch_patterns`` — Patterns for changed files.
- ``watch_ignore_patterns`` — Patterns for changed files to ignore.
- ``watch_debounce`` — Seconds to wait after a change before re-running.
- ``watch_recursive`` — Whether to watch directories recursively.

Task-defined values remain lists.  Both task-defined paths and CLI paths resolve
relative to the task's effective ``wd``.  Subprocess tasks use their configured
``wd``; other tasks use the invocation directory.  Only CLI pattern values are
split on ``;``; path values are passed literally.

Explicit CLI arguments (``--watch-paths``, ``--watch-patterns``, etc.)
always override task-defined defaults.

The quickie temporary directory is always excluded, so tasks writing to it do
not trigger an endless re-run loop.

When a change triggers a re-run, quickie prints the changed paths.  Use this
information to refine ``--watch-paths`` or ``--watch-ignore-patterns``.

Examples
--------

**Watch Python files and rebuild on change:**

.. code-block:: bash

   qk --watch --watch-paths src/ build

**Watch with a longer debounce for slow operations:**

.. code-block:: bash

   qk --watch --watch-debounce 2.0 deploy

**Watch only specific directories, excluding tests:**

.. code-block:: bash

   qk --watch --watch-paths src/ --watch-ignore-paths tests/ lint
