Conditions
==========

Conditions are used to determine if a task should run or not. They can be chained together with logical operators to create complex conditions.

Logical operators:

* ``&`` for AND
* ``|`` for OR
* ``~`` for NOT
* ``^`` for XOR

.. code-block:: python

    from quickie import task, conditions

    @task(condition=conditions.FirstRun() & conditions.PathsExist("file1", "file2"))
    def some_task():
        print("This task will run only the first time and if both files exist.")


You can use built-in conditions from :mod:`quickie.conditions` or create your own by subclassing :class:`quickie.conditions.base.BaseCondition` and
implementing the :meth:`quickie.conditions.base.BaseCondition.__call__` method, which should return ``True`` if the condition passes, ``False`` otherwise.
Additionally the :meth:`quickie.conditions.base.BaseCondition.__call__` must accept the task as an argument, and the arguments passed to the task.

You can also use the :func:`quickie.conditions.condition` decorator to create a condition from a function.

Builtin conditions:

* :class:`quickie.conditions.All` - Accepts other conditions and returns True if all of them pass. This is a shortcut for using the & operator.
* :class:`quickie.conditions.FirstRun` - Returns True if the task has not been run before. Optionally checks if it has been run with the same arguments.
* :class:`quickie.conditions.FilesModified` - Returns True if any of the files have been modified since the last run. Accepts folder, and excluding files.
* :class:`quickie.conditions.PathsExist` - Returns True if all the paths exist.
