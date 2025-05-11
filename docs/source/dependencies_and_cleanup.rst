Dependencies and Cleanup
========================

Tasks can depend on other tasks (or simple functions). This is useful when you want to run a task only if another task has run successfully, or if you want to run cleanup tasks.

.. code-block:: python

    from quickie import task

    @task
    def task1():
        print("Task 1")

    @task(before=[task1])
    def task2():
        print("Task 2")

    @task(after=[task2], cleanup=[lambda: cleanup()])
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

Before, After and Cleanup Tasks will not take the arguments from the parent. If you need to pass arguments :func:`functools.partial` or a lambda
function can be used. You can also override :meth:`Task.get_before`, :meth:`Task.get_after`, and :meth:`Task.get_cleanup` methods to
dynamically get the dependencies and any arguments.

.. code-block:: python

    from quickie import task, Task

    @task
    def task1(*args, **kwargs):
        print(f"{args=}, {kwargs=}")

    @task(after=[lambda: task1("arg1", kwarg="value")])
    def task2():
        print("Task 2")

    @task
    class MyTask(Task):
        def get_before(self, *args, **kwargs):
            # Args and kwargs are forwarded to task1
            yield lambda: task1(*args, **kwargs)

        def run(self, *arg, **kwargs):
            print("My task")
