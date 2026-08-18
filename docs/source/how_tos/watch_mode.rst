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
   Glob patterns or directories to watch.  Repeatable.  Defaults to the
   project root (the parent of the ``_qk`` directory).

   .. code-block:: bash

      qk --watch --watch-paths src/ --watch-paths lib/ my-task

``--watch-exclude PATTERN``
   Glob patterns or directories to exclude.  Repeatable.  Defaults to
   ``.git``, ``__pycache__``, ``*.pyc``, ``.quickie_cache``, ``tmp``.

   .. code-block:: bash

      qk --watch --watch-exclude build/ --watch-exclude vendor/ my-task

``--watch-debounce SECS``
   Seconds to wait after a change before re-running (default: ``0.5``).
   Prevents rapid re-runs when an IDE auto-formats multiple files on save.

   .. code-block:: bash

      qk --watch --watch-debounce 1.0 my-task

``--watch-interval SECS``
   Seconds between file-change polls (default: ``0.25``).  Lower values make
   watch mode more responsive but use more CPU.

   .. code-block:: bash

      qk --watch --watch-interval 0.1 my-task

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

Instead of passing ``--watch-paths`` and ``--watch-exclude`` on every
invocation, you can declare them directly on the task.  When ``qk --watch``
is used, the CLI picks up these defaults automatically.

**Using the ``@task`` decorator:**

.. code-block:: python

   from quickie import task

   @task(
       watch_paths=["src/"],
       watch_exclude=["tests/", "__pycache__"],
       watch_debounce=1.0,
       watch_interval=0.5,
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
       watch_exclude = ["tests/"]

       def get_cmd_args(self):
           return ["ruff", "check", "src/"]

Available watch attributes (used as defaults when ``--watch`` is passed):

- ``watch_paths`` — Glob patterns or directories to watch.
- ``watch_exclude`` — Patterns to exclude from watching.
- ``watch_debounce`` — Seconds to wait after a change before re-running.
- ``watch_interval`` — Seconds between file-change polls.

Explicit CLI arguments (``--watch-paths``, ``--watch-exclude``, etc.)
always override task-defined defaults.

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

   qk --watch --watch-paths src/ --watch-exclude tests/ lint
