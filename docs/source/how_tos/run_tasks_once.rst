Run tasks once
==================

Sometimes you want to avoid running a task if it has already been run, with or without the same arguments.

Quickie provides a way to memoize tasks by using the :class:`quickie.conditions.FirstRun` condition.
By default the arguments are not taken into account, but this can be accomplished by setting ``check_args`` to ``True``.

.. code-block:: python

    from quickie import task, FirstRun

    @task(condition=FirstRun())
    def my_task():
        print("This will only run the first time")

    @task(condition=FirstRun(check_args=True))
    def my_task_with_args(arg):
        print(f"This will only run the first time with arg: {arg}")


In a similar way, you can use the :class:`quickie.conditions.FilesModified` condition to only run a task if certain files have been modified since the last run.

.. code-block:: python

    from quickie import task, FilesModified

    @task(condition=FilesModified(["file1.txt", "file2.txt", "folder"], exclude=["folder/other.txt"]))
    def my_task():
        print("This will only run if file1.txt, file2.txt or any file under folder, except folder/other.txt, have been modified")
