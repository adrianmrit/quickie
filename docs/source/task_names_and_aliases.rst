Task names and aliases
======================

By default the task name is the function/class name. You can change the task name, or add aliases, by passing the `name` argument to the task decorator.
Note that the name of the function/class is not preserved, so you will need to pass it explicitly if you want to use it.

.. code-block:: python

    from quickie import task

    @task(name="my_task")
    def task1():
        print("Task 1")

    @task(name=["task2", "t2"])
    def task2():
        print("Task 2")

    # This will run task1
    qk my_task

    # These will run task2
    qk task2
    qk t2


Equivalent to:

.. code-block:: python

    from quickie import Task

    class MyTask(Task, name="my_task"):
        pass

    class Task2(Task, name=["task2", "t2"]):
        pass


.. WARNING::
    Inheriting from a task does not preserve the name or aliases. You will need add them again for each subclass.
    This way we avoid accidentally overwriting the name of the task.

.. WARNING::
    The last loaded tasks will take precedence. This means that if you have two tasks with the same name, the last one will be used.
