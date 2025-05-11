Task names and aliases
======================

By default the task name is the function/class name. You can change the task name, or add aliases, by passing the `name` and `alias` arguments to the task decorator.

.. code-block:: python

    from quickie import task

    @task(name="my_task")
    def task1():
        print("Task 1")

    @task(name="task2", alias=["t2"])
    def task2():
        print("Task 2")

    # This will run task1
    qk my_task

    # These will run task2
    qk task2
    qk t2


Or with task classes.

.. code-block:: python

    from quickie import Task

    @task(name="my_task")
    class MyTask(Task):
        pass

    @task(name="task2", alias=["t2"])
    class Task2(Task):
        pass

.. WARNING::
    The last loaded tasks will take precedence.
