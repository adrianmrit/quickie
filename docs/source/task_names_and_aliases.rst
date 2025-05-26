Task names and aliases
======================

By default the task name is the function/class name, with underscores and contiguous underscores
replaced by a single dash, and leading and trailing dashes removed, as to make it a friendlier name.

You can change the task name, or add aliases, by passing the `name` and `alias` arguments to the task decorator,
and these will not be transformed in any way.

.. WARNING::
    There is no restriction on what the name and alias can be, but it is recommended to avoid strings
    that would require quoting or escaping in the shell.

For example if defining the following tasks:

.. code-block:: python

    from quickie import task

    @task
    def _Task__1_():
        print("Task 1")

    @task(name="_Task__2")
    def task2():
        print("Task 2")

    @task(alias=["t3"])
    def task3():
        print("Task 2")


We can run them from the command line as follows:

.. code-block:: shell

    $ quickie task-1
    Task 1

    $ quickie _Task__2
    Task 2

    $ quickie task3
    Task 3

    $ quickie t3
    Task 3


Name conflicts
--------------
If two tasks have the same name, the last one defined will be used.

.. code-block:: python

    from quickie import task

    @task(name="task")
    def task1():
        print("Task 1")

    @task(name="task")
    def task2():
        print("Task 2")

.. code-block:: shell

    $ quickie task
    Task 2
