Dependencies between tasks
==========================

Tasks can depend on other tasks. This is useful when you want to run a task only if another task has run successfully, or if you want to run cleanup tasks.

.. code-block:: python

    from quickie import task

    @task
    def task1():
        print("Task 1")

    @task(before=[task1])
    def task2():
        print("Task 2")

    @task(after=[task2], cleanup=["cleanup"])
    def task3():
        print("Task 3")

    @task
    def cleanup():
        print("Cleanup")

The tasks are executed in the following order:

1. Before tasks
2. The task itself
3. After tasks
4. Cleanup tasks

If a task fails, the cleanup tasks will still run. And if one of the cleanup tasks fails, the rest of the cleanup tasks will still run.

Tasks ran as a dependency will not inherit the arguments from the tasks that depend on them. If you need to pass arguments :func:`quickie.partial_task`
can be used to create a task with predefined arguments. You can also override `get_before`, `get_after`, and `get_cleanup` methods to dynamically set the dependencies.

.. code-block:: python

    from quickie import task, partial_task, Task

    @task
    def task1(*args, **kwargs):
        print(f"{args=}, {kwargs=}")

    @task(after=[partial_task(task1, "arg1", kwarg="value")])
    def task2():
        print("Task 2")

    class MyTask(Task):
        def get_before(self, *args, **kwargs):
            # Args and kwargs are forwarded to task1
            yield partial_task(task1, *args, **kwargs)

        def run(self, *arg, **kwargs):
            print("My task")
