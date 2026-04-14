Script
======

Script tasks are similar to command tasks, but they will run the script in the shell, instead of running a subprocess. This allows
for more complex scripts, and for the use of shell features such as pipes, redirections, etc, if the shell supports them.

The shell used to run the script is platform dependent by default, but can be changed by setting the ``executable`` attribute of the task.

Default shells per platform:

- Windows: ``cmd.exe``
- Linux: ``/bin/sh``
- MacOS: ``/bin/sh``

.. warning::

    Passing arguments to scripts can be dangerous, as they can be used to inject code. Be careful when using them.

.. tip::

    Python supports many of the features of shell scripts, and is usually cross platform and safer. If you can, try to use Python code instead of shell scripts.


.. code-block:: python

    from quickie import script

    @script
    def hello_script():
        return "echo 'Hello, World!'"


This will return a :class:`quickie.tasks.Script` instance, equivalent to:

.. code-block:: python

    from quickie import Script

    class HelloScript(Script):
        def get_script(self):
            return "echo 'Hello, World!'"


To pass arguments you can simply use string formatting:

.. code-block:: python

    from quickie import script, Arg

    @script(args=[
        Arg("name"),
    ])
    def hello_script(name):
        return f"echo 'Hello, {name}!'"


Setting the ``executable`` attribute of the task will change the shell used to run the script:

.. code-block:: python

    from quickie import script

    @script(executable="python")
    def hello_script():
        return "print('Hello, World!')"


Exit codes
----------

Script tasks validate shell exit codes strictly by default. Exit code ``0`` is accepted, and any other exit code raises an error that exits the CLI with the same code.

If a script intentionally uses a non-zero exit code, allow it explicitly with ``expected_exit_codes``:

.. code-block:: python

    from quickie import script

    @script(expected_exit_codes=(0, 5))
    def script_with_expected_failure():
        return "exit 5"

The same option is available on subclasses by setting the ``expected_exit_codes`` attribute.

To disable exit-code validation completely, set ``expected_exit_codes`` to ``None`` or ``()``.
