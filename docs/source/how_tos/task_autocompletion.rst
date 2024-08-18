Task Autocompletion
===================

Tasks already have some autocompletion built in, such as for flags and arguments.

Autocompletion can also be enabled for individual parameters by passing the `completer` argument to the `arg` decorator.

.. code-block:: python

    from quickie import arg, task
    from quickie.completion import PathCompleter

    @task
    @arg("--path", help="A path", completer=PathCompleter())
    def some_task(path):
        print(f"Path: {path}")

Or if overriding :meth:`quickie.tasks.Task.add_args`:

.. code-block:: python

    from quickie import task
    from quickie.completion import PathCompleter

    class SomeTask(task.Task):
        def add_args(self, parser):
            parser.add_argument("--path", help="A path").completer=PathCompleter()

        def run(self):
            print(f"Path: {self.args.path}")

This will add path autocompletion to the `--path` argument.

Some completers are provided by Quickie, such as :class:`quickie.completion.PathCompleter` and :class:`quickie.completion.python.PytestCompleter`.
You can also create your own completers by subclassing :class:`quickie.completion.base.BaseCompleter` and implementing the :meth:`quickie.completion.base.BaseCompleter.complete` method.
