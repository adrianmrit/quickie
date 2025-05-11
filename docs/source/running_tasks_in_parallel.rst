Running Tasks in Parallel
=========================

Thread group tasks are used to run multiple tasks in parallel.
The simplest way is to use the :func:`quickie.thread_group` decorator to define a thread group task:

.. code-block:: python

    from quickie import thread_group

    def task1():
        print("Task 1")

    @task
    def task2():
        print("Task 2")

    @thread_group
    def my_thread_group():
        return [task1, task2]


This will return a :class:`quickie.tasks.ThreadGroup` instance, equivalent to:

.. code-block:: python

    from quickie import ThreadGroup

    ...

    @task
    class my_thread_group(ThreadGroup):
        def get_tasks(self):
            return [task1, task2]

If one of these tasks fails, the other tasks will continue to run.

.. WARNING::
    Under the hood, this uses Python threads. This means that pure Python tasks, particularly those that are CPU-bound, will be
    affected by the Global Interpreter Lock (GIL), thus not necessarily running faster than in sequence. For I/O-bound tasks, however,
    this can be a good way to speed up your tasks. Similarly, subprocesses created by tasks will not be affected by the GIL.
