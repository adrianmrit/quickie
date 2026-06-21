Task Autocompletion
===================

Tasks already have some autocompletion built in, such as for flags and arguments.

Autocompletion can also be enabled for individual parameters by passing the ``completer`` argument to the ``arg`` decorator.

.. code-block:: python

    from quickie import Arg, task
    from quickie.completion import PathCompleter

    @task(args=[
        Arg("--path", help="A path", completer=PathCompleter()),
    ])
    def some_task(path):
        print(f"Path: {path}")

The :class:`~quickie.completion.PathCompleter` accepts an optional ``wd`` parameter
to control which directory paths are resolved relative to, following the same
rules as task working directories:

.. code-block:: python

    # Resolve relative to the tasks module parent directory
    Arg("--path", completer=PathCompleter(wd="."))
    Arg("--path", completer=PathCompleter(wd="./subdir"))

    # Resolve relative to a specific absolute directory
    Arg("--path", completer=PathCompleter(wd="/absolute/path"))

    # Resolve relative to the current working directory (default)
    Arg("--path", completer=PathCompleter())
    Arg("--path", completer=PathCompleter(wd="relative/to/cwd"))

When ``wd`` is ``None`` (the default), completion resolves relative to the
current working directory, preserving the existing behaviour.

Some completers are provided by Quickie, such as :class:`quickie.completion.PathCompleter` and :class:`quickie.completion.python.PytestCompleter`.
You can also create your own completers by subclassing :class:`quickie.completion.base.BaseCompleter` and implementing the :meth:`quickie.completion.base.BaseCompleter.complete` method.
