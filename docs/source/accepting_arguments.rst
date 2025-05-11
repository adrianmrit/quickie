Accepting arguments
===================

You can define command line arguments for your tasks by using the `args` parameter in the task decorator.

The ``args`` parameter accepts a list containing either:

    - A string representing the argument name (e.g. ``--name``).
    - A tuple containing the argument name and a shortcut (e.g. ``("--name", "-n")``).
    - An instance of ``Arg`` (e.g. ``Arg("--name", "-n")``), useful for more complex arguments.

In addition, you can pass ``extra_args=True`` to the task decorator to allow unknown arguments to be passed to the task.

Arguments will be automatically parsed when the task is run, and passed as keyword arguments to the task function. If
``extra_args=True`` is set, the unknown arguments will be passed as positional arguments.

.. code-block:: python

    from quickie import Arg, task

    @task(
        args=[
            ("--name", "-n"),  # Shortcut for Arg("--name", "-n")
            "--age",  # Shortcut for Arg("--age")
        ]
    )
    def hello(name, age):
        print(f"Hello, {name}! You are {age} years old.")

    @task(
        args=[
            Arg("--flag", help="A flag", action="store_true"),
        ],
        extra_args=True
    )
    def with_extra_args(*args, flag=False):
        print(f"{args=}, {flag=}")


Forcing positional arguments
----------------------------

Sometimes when calling a task you want to force an argument to be treated as positional, even if it is defined as a keyword argument.
This can be done by adding the arguments after ``--``.

For example, if you have a task defined as:

.. code-block:: python

    @command(extra_args=True)
    def commit(*args):
        return ["git", "commit", *args]

If you try to get the help message from ``git commit``, you might try running ``qk commit --help``, however this will
will show the help message from our task instead. So what you want to do is run ``qk commit -- --help``, which will
result in ``--help`` being passed as a positional argument to the task.


Auto completion
----------------

You can also define auto-completion for your task arguments. This is done by passing a ``completer`` argument to the ``Arg`` instance.
Refer to the :doc:`task autocompletion <how_tos/task_autocompletion>` section for more information.


Under the hood
----------------

Under the hood each Task defines an `argparse.ArgumentParser <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser>`_ instance.
The ``Arg`` class is a simple wrapper around `argparse.ArgumentParser.add_argument <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument>`_
that allows you to define the arguments in a more convenient way and accepts the same arguments as `argparse.ArgumentParser.add_argument <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument>`_.
The only additional argument is ``completer``, which is used for :doc:`task autocompletion <how_tos/task_autocompletion>`.

This should be enough for most use cases, but you can still inherit from ``Arg`` and override the ``add`` and ``set_completer`` methods to customize how
the argument is added to the parser and how the completer is set.

Please refer to
`argparse.ArgumentParser.add_argument <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument>`_
for more information on the available arguments.
