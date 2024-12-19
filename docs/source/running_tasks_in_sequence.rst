Running tasks in sequence
=========================

Group tasks are used to run multiple tasks in sequence.
The simplest way is to use the :func:`quickie.group` decorator to define a group task, which should return a list of tasks:

.. code-block:: python

    from quickie import group, lazy_task

    @task
    def task1():
        print("Task 1")

    @task
    def task2():
        print("Task 2")

    @group
    def my_group():
        return [
            lazy_task("task1"),
            task2,
        ]


This will return a :class:`quickie.tasks.Group` instance, equivalent to:

.. code-block:: python

    from quickie import Group

    class MyGroup(Group):
        def get_tasks(self):
            return [
                lazy_task("task1"),
                task2,
            ]

If one of these tasks fails, no further tasks will be run.
