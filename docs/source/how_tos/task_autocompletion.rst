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

Some completers are provided by Quickie, such as :class:`quickie.completion.PathCompleter` and :class:`quickie.completion.python.PytestCompleter`.
You can also create your own completers by subclassing :class:`quickie.completion.base.BaseCompleter` and implementing the :meth:`quickie.completion.base.BaseCompleter.complete` method.
