Private tasks
=============

Private tasks are tasks that are not meant to be run directly. You can define private tasks by prefixing the task name with an underscore.

.. code-block:: python

    from quickie import task

    @task
    def _private_task():
        print("Private task")


Same with classes:

.. code-block:: python

    from quickie import Task

    class _PrivateTask(Task):
        def run(self):
            print("Private task")


Sometimes however, we don't want to prefix the task name with an underscore, i.e. when we want to use the task as a base class
for other tasks. We can also make tasks private by setting `private=True` in the class definition.

.. code-block:: python

    from quickie import Task

    class BaseTask(Task, private=True):
        pass


.. WARNING::
    The privacy of a task is not inherited. This means that if you subclass a private task, the subclass will not be private.
    This allows to easily inherit from private tasks without having to explicitly set ``private=False``.
