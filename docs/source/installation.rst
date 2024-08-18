Installation
============

Python version
--------------
Quickie requires Python 3.12 or higher.


Per Project Installation
------------------------

For projects Quickie can either be installed in the same environment as your project, if it already has one
and is for a compatible Python version, or in a separate virtual environment. By using a virtual environment
you can isolate your dependencies for that specific project, and use different versions of Quickie for different
projects without conflicts.

.. code-block:: bash

    python -m venv .venv
    source .venv/bin/activate
    pip install quickie-runner
    qck --help


Global installation
-------------------

For global installation, it is recommended to install `quickie-runner-global <https://pypi.org/project/quickie-runner-global/>`_. This will
add a separate `qckg` command to your system, thus not conflicting with `qck` when you want
to run global tasks from inside a project. It also installs `quickie-runner <https://pypi.org/project/quickie-runner/>`_ as a dependency.

You can do this install for the Global Python installation, or use `pipx` to create an isolated
environment for the global installation.


With pip
^^^^^^^^

.. code-block:: bash

    pip install quickie-runner-global
    qckg --help


With pipx

.. code-block:: bash

    pipx install quickie-runner-global
    qckg --help

If you need to add extra dependencies to your global tasks, you can inject them:

.. code-block:: bash

    pipx inject quickie-runner-global my-extra-dependency

See `pipx <https://pipx.pypa.io/stable/>`_ for more information.


Auto completion
---------------
Quickie provides auto completion for tasks and arguments via the `argcomplete <https://pypi.org/project/argcomplete/>`_ package.

To enable it, you need to install `argcomplete` and add the following line to your shell configuration file:

.. code-block:: bash

    eval "$(register-python-argcomplete qck)"


This will enable auto completion for the `qck` command. If you have a global installation, you can enable auto completion for the `qckg` command as well:

.. code-block:: bash

    eval "$(register-python-argcomplete qckg)"

You can also call ``qck --autocomplete bash`` or ``qck --autocomplete zsh`` for instructions on how to enable auto completion for your shell.
