Command
=======

Command tasks run subprocesses. The simplest way is to use :func:`quickie.command` decorator to define a task.
The decorated function should return either a string of command and arguments in POSIX shell format, or a list of strings.

.. code-block:: python

    from quickie import command

    @command
    def command_from_string():
        return "my_command arg1 arg2"

    @command
    def command_from_list():
        return ["my_command", "arg1", "arg2"]

To create a command from a class, inherit from :class:`quickie.tasks.Command` and replace the :meth:`quickie.tasks.Command.get_cmd` method.
Or, replace the :meth:`quickie.tasks.Command.get_binary` and :meth:`quickie.tasks.Command.get_cmd_args` methods.

For example the followings are all equivalent:

.. code-block:: python

    from quickie import Command

    @task
    class SomeCommand(Command):
        def get_cmd(self):
            return "my_command arg1 arg2"  # or ["my_command", "arg1", "arg2"]

    @task
    class SomeCommand(Command):
        def get_binary(self):
            return "my_command"

        def get_cmd_args(self):
            return "arg1 arg2"  # or ["arg1", "arg2"]


Exit codes
----------

Command tasks validate subprocess exit codes strictly by default. Exit code ``0`` is accepted, and any other exit code raises an error that exits the CLI with the same code.

If a command is expected to return a non-zero code, allow it explicitly with ``expected_exit_codes``:

.. code-block:: python

    from quickie import command

    @command(expected_exit_codes=(0, 2))
    def grep_with_no_match_allowed():
        return ["grep", "-q", "pattern", "file.txt"]

The same option is available on subclasses by setting the ``expected_exit_codes`` attribute.

To disable exit-code validation completely, set ``expected_exit_codes`` to ``None`` or ``()``.

Timeout
-------

To limit how long a single subprocess attempt may run, set ``timeout`` (in seconds):

.. code-block:: python

    from quickie import command

    @command(timeout=30)
    def long_running():
        return ["my_tool", "--process"]

If the subprocess does not finish within the allotted time, a
:exc:`~quickie.errors.SubprocessTimeoutError` is raised (exit code 124).
The same attribute is available on subclasses.

Retry
-----

To automatically retry a command after a transient failure, set ``retries`` to the
number of *additional* attempts:

.. code-block:: python

    from quickie import command

    @command(retries=3)
    def flaky_network_call():
        return ["curl", "https://example.com/api"]

An optional ``retry_delay`` (in seconds) can be added to wait between attempts:

.. code-block:: python

    @command(retries=3, retry_delay=2.0)
    def flaky_network_call():
        return ["curl", "https://example.com/api"]

Retries are triggered by both :exc:`~quickie.errors.SubprocessExitCodeError` and
:exc:`~quickie.errors.SubprocessTimeoutError`. If all attempts fail, the last
exception is re-raised. A warning is logged for each failed attempt and each retry.
Both attributes are available on subclasses.
