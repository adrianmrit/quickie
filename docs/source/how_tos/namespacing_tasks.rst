Namespacing tasks
=================

Namespacing is useful when you have a large number of tasks and want to organize them into logical groups.

The best way to namespace is to add a ``NAMESPACES`` dictionary `__quickie/__init__.py`:

.. code-block:: python

    # MyProject/__quickie/__init__.py
    from . import public, tests

    NAMESPACES = {
        "": [public],
        "p": [],
        "tests": tests,
    }

    try:
        from . import private
        NAMESPACES[""].append(private)
        NAMESPACES["private"].append(private)
    except ImportError:
        pass

In this example, the ``private`` module is optional. If it exists, tasks from it will be added to the
root namespace, and also to a namespace called ``p``. If it doesn't exist, the namespace will be empty.

Note that if a list of namespaces is given, the tasks will be loaded in the order they are defined, meaning
that the last module in the list will take precedence. This is useful when you want to override tasks from
another module, i.e. here the private tasks might override the public ones.

Assuming the ``private`` module exists, then you can run tasks using the namespace as a prefix:

.. code-block:: bash

    quickie p.task1

Or, since the private module is loaded under the root namespace, you can also run:

.. code-block:: bash

    quickie task1

For the ``tests`` module however, they are only available under the ``tests`` namespace.

Another option is do define the namespace as part of the task name:

.. code-block:: python

    from quickie import task

    @task(name=["task1", "p.task1"])
    def task1():
        print("Task 1")


This will make ``task1`` available under both the root namespace and the ``p`` namespace.
This however is not as clear and is harder to change.
