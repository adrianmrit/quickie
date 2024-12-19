Namespaces
==========

When having a large number of tasks, it's useful to organize them into logical groups.
The best way to do so is to create separate modules for each group of tasks and then import them at the root level.
While we could simple import all tasks from the modules, there is a chance of name conflicts and can create
confusion. To avoid this, we can use namespaces.

Namespaces are defined via a `NAMESPACES` mapping in the tasks file:

.. code-block:: python

    # MyProject/__quickie/__init__.py
    from . import public, private, tests
    try:
        from . import private
    except ImportError:
        private = None

    NAMESPACES = {
        "": [public, private],
        "private": private,
        "tests": tests,
    }


As you can see in this example, we ignore null values for convenience. Here the `private` module is optional.

.. WARNING::
    If a list of namespaces is given, the tasks will be loaded in the order they are defined, meaning
    that the last module in the list will take precedence. This is useful when you want to override tasks from
    another module, i.e. here the private tasks might override the public ones.

.. WARNING::
    ``NAMESPACES`` is always handled first and should be defined before any other tasks. As such, if there are any
    tasks either before or after the `NAMESPACES` definition, they can overwrite tasks from the namespaces. This
    includes tasks with names or aliases that are namespace like.
