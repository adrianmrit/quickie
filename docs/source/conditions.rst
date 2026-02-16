Conditions
==========

Conditions are used to determine if a task should run or not. There are some built-in conditions provided by Quickie, and you can also create your own.


FirstRun
--------

The :class:`quickie.conditions.FirstRun` condition is used to run a task only the first time it is called, or the first time with specific arguments if ``check_args`` is set to ``True``.
It is useful for tasks that should not be repeated, such as initialization tasks or one-time setup.

It can be used as follows:

.. code-block:: python

    from quickie import task, FirstRun

    @task(condition=FirstRun())
    def my_task():
        print("This will only run the first time")

    @task(condition=FirstRun(check_args=True), extra_args=True)
    def my_task_with_args(*args):
        print(f"This will only run the first time with args: {args}")


FilesModified
-------------

The :class:`quickie.conditions.FilesModified` condition is used to run a task only if certain files have been modified since the last run.
It can be used to ensure that tasks are only run when necessary, such as when a requirement file has changed.

It can be used as follows:

.. code-block:: python

    from quickie import task, FilesModified

    @task(condition=FilesModified("cache_unique_identifier", paths=["file1.txt", "file2.txt", "folder"], exclude=["folder/other.txt"]))
    def my_task():
        print("This will only run if file1.txt, file2.txt or any file under folder, except folder/other.txt, have been modified")


:class:`quickie.conditions.FilesModified` takes the following parameters:

- ``cache_id``: The identifier of the condition, used as part of the cache file
  name. It should be unique for each condition instance to avoid conflicts. It
  is recommended to be something that groups the files being checked, or a
  random string like an UUID.
- ``paths``: The files to check.
- ``exclude``: The files to exclude from the check.
- ``algorithm``: The algorithm to use for checking. Can be one of :class:`quickie.FilesModified.Algorithm` or a string representing the algorithm name, such as ``md5``, ``sha1``, ``sha256``, or ``timestamp``.
- ``allow_missing``: If True, missing files will be treated as if they have not been modified. Defaults to False.


PathsExist
----------

The :class:`quickie.conditions.PathsExist` condition is used to run a task only if all specified paths exist.
It can be used to ensure that tasks are only run when certain files or directories are present.

It can be used as follows:

.. code-block:: python

    from quickie import task, PathsExist

    @task(condition=PathsExist("file1.txt", "file2.txt", "folder"))
    def my_task():
        print("This will only run if file1.txt, file2.txt and folder exist")


All
---

The :class:`quickie.conditions.All` condition is a convenience class that allows you to combine multiple conditions and return True only if all of them pass.
It can be used as follows:

.. code-block:: python

    from quickie import task, conditions

    @task(condition=conditions.All(conditions.FirstRun(), conditions.PathsExist("file1.txt", "file2.txt")))
    def some_task():
        print("This task will run only the first time and if both files exist.")


Custom conditions
-----------------

Custom conditions can be created from a function by using the :func:`quickie.conditions.condition` decorator, or by subclassing :class:`quickie.conditions.BaseCondition`.

For example:

.. code-block:: python

    import os
    from quickie import task, conditions

    @conditions.condition
    def my_custom_condition(task, *args, **kwargs):
        # Custom logic to determine if the task should run
        return os.getenv("RUN_MY_TASK", "true").lower() == "true"

    class SimpleCondition(conditions.BaseCondition):
        def __init__(self, run=True):
            self.run = run

        def __call__(self, task, *args, **kwargs):
            return self.run

    @task(condition=my_custom_condition)
    def my_task():
        print("This task runs only if my_custom_condition returns True.")

    @task(condition=SimpleCondition(os.getenv("RUN_MY_OTHER_TASK", "true").lower() == "true"))
    def another_task():
        print("This task runs only if SimpleCondition returns True.")


Combining conditions
--------------------

Conditions can be combined using the following logical operators:

* ``&`` for AND
* ``|`` for OR
* ``~`` for NOT
* ``^`` for XOR

.. code-block:: python

    from quickie import task, conditions

    @task(condition=conditions.FirstRun() | conditions.FilesModified("cache_unique_identifier", paths=["file1.txt", "file2.txt"]))
    def some_task():
        print("This task will run only the first time or if any of the files have been modified.")


Skipping conditions
----------------------------

Conditions cannot be skipped directly, but since you can call conditions in the body of a task, you can implement something like the following:

.. code-block:: python

    from quickie import task, conditions, Arg, errors

    @task
    def my_before_requirement():
        print("Running before requirement...")

    @task
    def my_after_requirement():
        print("Running after requirement...")

    @task
    def my_cleanup_requirement():
        print("Running cleanup requirement...")

    @task(
        args=Arg("-f", "--force", action="store_true", help="Force run the task"),
        bind=True,
    )
    def my_task(task, force=False):
        if force or conditions.FirstRun()(task):
            # Run requirements only if the task is actually going to run
            try:
                my_before_requirement()
                print("This task will run because it is forced or the first run condition is met.")
                my_after_requirement()
            finally:
                my_cleanup_requirement()
        else:
            raise errors.Skip("Task already run.")
