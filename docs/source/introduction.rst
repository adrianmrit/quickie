Introduction
============

Quickie is a simple task runner, inspired on tools like `cargo-make <https://github.com/sagiegurari/cargo-make>`_,
`Task <https://taskfile.dev>`_, and `invoke <https://www.pyinvoke.org>`_.
It aims to be simple to use, easy to extend, and to provide a good experience for developers and teams.

Unlike other task runners that define tasks in YAML, TOML or specialized formats, Quickie uses the Python programming language
directly, leveraging the power of the language and the ecosystem around it. This means for example, that syntax highlighting,
errors, and auto completion in most code editors will work out of the box. Still, Quickie is not limited to Python projects.

Some features include:

* Run python, shell scripts, and subprocesses as tasks.
* Powerful arguments parsing, by wrapping `argparse <https://docs.python.org/3/library/argparse.html>`_.
* Autocompletion both for the CLI and the individual tasks, thanks to `argcomplete <https://pypi.org/project/argcomplete/>`_.
* Custom autocompletion for task arguments.
* Conditions to control when or if a task should run.
* Dependencies between tasks.
* Namespaces to organize tasks.

Requirements
--------------
Quickie works with macOS, Linux and Windows. Python 3.12 or higher is required.


Per Project Installation
------------------------

You can install Quickie with pip or your favorite package manager. For projects, it is usually better to install
Quickie in a virtual environment. By using a virtual environment you can isolate your dependencies for that specific
project, and use different versions of Quickie for different projects without conflicts.

.. code-block:: bash

    python -m venv .venv
    source .venv/bin/activate
    pip install quickie-runner
    qk --help


Global installation
-------------------

While Quickie allows to run tasks defined between a project, sometimes it is useful to have tasks defined globally and run them
from anywhere. `quickie-runner-global <https://pypi.org/project/quickie-runner-global/>`_ is a package that allows to do just that.

This is a wrapper around `quickie-runner` that will add a separate `qkg` command, thus not conflicting with `qk`. Tasks in this case
need to be defined at `~/_qkg`.

You can do this install for your default Python installation, or use `pipx <https://pipx.pypa.io/stable/>`_ to create an isolated
environment.


With pip
^^^^^^^^

.. code-block:: bash

    pip install quickie-runner-global
    qkg --help


With pipx

.. code-block:: bash

    pipx install quickie-runner-global
    qkg --help

.. TIP::
    If installing via PIPX and you need to add extra dependencies, you can inject them:

    .. code-block:: bash

        pipx inject quickie-runner-global my-extra-dependency


Upgrading
---------

You can also upgrade via `pip`:

.. code-block:: bash

    pip install --upgrade quickie-runner


Or `pipx`:

.. code-block:: bash

    pipx upgrade quickie-runner


Auto completion
---------------
Quickie provides auto completion for tasks and arguments via the `argcomplete <https://pypi.org/project/argcomplete/>`_ package.

To enable it, you need to install `argcomplete <https://pypi.org/project/argcomplete/>`_ globally and add the following line to your shell configuration file:

.. code-block:: bash

    eval "$(register-python-argcomplete qk)"


This will enable auto completion for the ``qk`` command. If you have a global installation, you can enable auto completion for the ``qkg`` command as well:

.. code-block:: bash

    eval "$(register-python-argcomplete qkg)"

You can also call ``qk --autocomplete bash`` or ``qk --autocomplete zsh`` for instructions on how to enable auto completion for your shell.


Quick(ie)start
--------------

Defining tasks
^^^^^^^^^^^^^^

Tasks can be defined in a `_qk` Python module, be it a single file or a package, usually at the
root of the project. For global tasks they can be defined in the same way at `~/_qkg`. They can also
be defined at an arbitrary Python module, and passed to the runner using the ``--module`` or ``-m`` argument.

For example:

.. code-block:: python

    # MyProject/_qk.py
    from quickie import Arg, task, script, command

    @task
    def hello():
        print("Hello, World!")

    @script(
        args=[
            Arg("--name", help="Your name"),
        ],
    )
    def hello_script(name):
        return f"echo 'Hello, {name}!'"

    @command(extra_args=True)
    def some_command(*args):
        return ["my_command", *args]

Now you can run the tasks from anywhere in the project, even from a subdirectory.

.. code-block:: bash

    $ qk hello
    Hello, World!

    $ qk hello_script --name Alice
    Hello, Alice!

    $ qk some_command arg1 arg2
    my_command arg1 arg2


Defining tasks in a package
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For more complex projects, or teams, it is recommended to define tasks in a package.
This allows to better organize the tasks and to have private tasks that are not
committed to the repository.

For example:

.. code-block:: bash

    MyProject/
    ├── _qk
    │   ├── __init__.py
    │   ├── public.py
    │   ├── private.py  # might not exist
    │   └── ...        # more files
    └── ...


Then in the ``__init__.py`` file you can import the tasks from the other files.

.. code-block:: python

    # MyProject/_qk/__init__.py
    from quickie import Namespace
    from . import public

    namespace = Namespace()
    try:
        from . import private
        namespace.add(private, "private")
    except ImportError:
        pass

    namespace.add(public)


For most of of the documentation, we will assume tasks are defined in a package.
