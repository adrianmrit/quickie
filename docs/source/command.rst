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
