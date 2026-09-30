Command-line interface
=======================

Run a task directly with its name and arguments:

.. code-block:: bash

   qk my-task arg1 arg2

Place Quickie options before the task name. All arguments after the task name
are forwarded unchanged to the task, including options such as ``--help``.

Operational commands use a colon prefix so task names never conflict with
reserved CLI commands:

``qk :list [--filter TEXT] [--json]``
   List available tasks. ``--json`` is intended for integrations.

``qk :watch [WATCH OPTIONS] TASK [ARGS...]``
   Run a task and rerun it when watched files change. See
   :doc:`how_tos/watch_mode`.

   Watch options are ``--paths``, ``--ignore-paths``, ``--patterns``,
   ``--ignore-patterns``, ``--recursive``, and ``--debounce``.
   Place these options before ``TASK``; options after it belong to the task.

``qk :init [DIR]``
   Initialize a quickie project in ``DIR`` (the current directory by default).

``qk :autocomplete {bash,zsh}``
   Print shell setup instructions for argcomplete.

The previous action flags (such as ``-l``, ``--watch``, and ``--init``) are no
longer supported. Common options remain available for every invocation:
``-v``/``--verbose``, ``-q``/``--quiet``, ``--log-file``, ``-m``/``--module``,
and ``-g``/``--global``.
