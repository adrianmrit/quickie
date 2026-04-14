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

If one of these tasks fails, the other tasks will continue to run to completion.
Once all tasks have finished, any exceptions that were raised are collected and
re-raised together as a single :exc:`ExceptionGroup`:

.. code-block:: python

    import quickie

    @quickie.task
    def fail_a():
        raise ValueError("A went wrong")

    @quickie.task
    def fail_b():
        raise RuntimeError("B went wrong")

    @quickie.thread_group
    def my_group():
        return [fail_a, fail_b]

    @quickie.task
    def run_group():
        try:
            my_group()
        except* ValueError as eg:
            print("ValueError(s):", eg.exceptions)
        except* RuntimeError as eg:
            print("RuntimeError(s):", eg.exceptions)

This means **no exception is silently discarded** — every failure from every
concurrent task is surfaced.  Use Python 3.11+ ``except*`` syntax to handle
particular exception types, or catch ``ExceptionGroup`` to inspect them all.

.. WARNING::
    Under the hood, this uses Python threads. This means that pure Python tasks, particularly those that are CPU-bound, will be
    affected by the Global Interpreter Lock (GIL), thus not necessarily running faster than in sequence. For I/O-bound tasks, however,
    this can be a good way to speed up your tasks. Similarly, subprocesses created by tasks will not be affected by the GIL.
