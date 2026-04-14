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

Timeout
-------

To limit how long a single script attempt may run, set ``timeout`` (in seconds):

.. code-block:: python

    from quickie import script

    @script(timeout=30)
    def long_script():
        return "my_tool --process"

If the script does not finish within the allotted time, a
:exc:`~quickie.errors.SubprocessTimeoutError` is raised (exit code 124).
The same attribute is available on subclasses.

Retry
-----

To automatically retry a script after a transient failure, set ``retries`` to the
number of *additional* attempts:

.. code-block:: python

    from quickie import script

    @script(retries=3)
    def flaky_script():
        return "curl https://example.com/api"

An optional ``retry_delay`` (in seconds) can be added to wait between attempts:

.. code-block:: python

    @script(retries=3, retry_delay=2.0)
    def flaky_script():
        return "curl https://example.com/api"

Retries are triggered by both :exc:`~quickie.errors.SubprocessExitCodeError` and
:exc:`~quickie.errors.SubprocessTimeoutError`. If all attempts fail, the last
exception is re-raised. A warning is logged for each failed attempt and each retry.
Both attributes are available on subclasses.

Capturing output
----------------

By default, script output streams directly to the terminal. Use
``output_mode`` to control this behaviour:

- ``"stream"`` *(default)* — output goes to the terminal; nothing is captured.
- ``"capture"`` — output is captured as bytes; nothing is printed.
- ``"tee"`` — output streams to the terminal *and* is captured.

Both :class:`~quickie.tasks.OutputMode` enum values and plain string literals
are accepted interchangeably:

.. code-block:: python

    from quickie import script, task, OutputMode

    # Using the enum
    @script(output_mode=OutputMode.CAPTURE)
    def get_version_enum():
        return "my_tool --version"

    # Using a string literal — equivalent to the above
    @script(output_mode="capture")
    def get_version_str():
        return "my_tool --version"

    # Tee — terminal sees output and it is also available afterwards
    @script(output_mode="tee")
    def verbose_build():
        return "make all"

    @task
    def print_version():
        result = get_version_str()      # CompletedProcess.stdout is bytes
        print(result.stdout.decode())

When subclassing, set ``output_mode`` as a class attribute using either form::

    class MyScript(Script):
        output_mode = OutputMode.CAPTURE  # or output_mode = "capture"

See also :ref:`calling-tasks-from-run` for the task composition pattern.
