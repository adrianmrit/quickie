Quickstart
==========

This page will guide you through the process of creating a new Quickie project.

Where to define tasks
---------------------

Tasks can be defined in a ``__quickie`` Python module, be it a single file or a package.
It does not need to be defined in the current working directory, Quickie will
also look across parent directories until it finds it or reaches the root directory.

For example:

.. code-block:: python

    # MyProject/__quickie.py
    from quickie import arg, task, script, command

    @task
    def hello():
        print("Hello, World!")

    @script
    @arg("--name", help="Your name")
    def hello_script(name):
        return f"echo 'Hello, {name}!'"

    @command(extra_args=True)
    def some_command(*args):
        return ["my_command", *args]

Now you can run the tasks from anywhere in the project, even from a subdirectory.

.. code-block:: bash

    $ qck hello
    Hello, World!

    $ qck hello_script --name Alice
    Hello, Alice!

    $ qck some_command arg1 arg2
    my_command arg1 arg2


Defining tasks in a package
---------------------------

For more complex projects, or teams, it is recommended to define tasks in a package.
This allows to better organize the tasks and to have private tasks that are not
committed to the repository.

For example:

.. code-block:: bash

    MyProject/
    ├── __quickie
    │   ├── __init__.py
    │   ├── public.py
    │   ├── private.py  # might not exist
    │   └── ...        # more files
    └── ...


Then in the ``__init__.py`` file you can import the tasks from the other files.

.. code-block:: python

    # MyProject/__quickie/__init__.py
    from . import public
    try:
        from . import private
    except ImportError:
        private = None

    NAMESPACES = {  # Namespaces tasks
        "": [public, private],  # private tasks will take precedence
        "private": ,  # private tasks also available under `private` namespace
    }


Function based vs Class based tasks
-----------------------------------

Tasks can be defined as functions, by using one of the task decorators, or as classes by subclassing :class:`quickie.tasks.Task` or one of its subclasses.

Functions decorated with :func:`quickie.task`, :func:`quickie.script`, and :func:`quickie.command` are equivalent to subclasses
of :class:`quickie.tasks.Task`, :class:`quickie.tasks.Script`, and :class:`quickie.tasks.Command` respectively. However, functions
are simpler to define and are recommended for most tasks.


Python Tasks
------------

You can define tasks that simply run Python code.
The simplest way is to use :func:`quickie.task` decorator to define a task:

.. code-block:: python

    from quickie import task

    @task
    def hello():
        print("Hello, World!")


This will return a :class:`quickie.tasks.Task` instance, equivalent to:

.. code-block:: python

    from quickie import Task

    class Task(Task):
        def run(self):
            print("Hello, World!")


Script Tasks
------------

Specialized subclass of tasks that run shell scripts.
The simplest way is to use :func:`quickie.script` decorator to define a task:

.. code-block:: python

    from quickie import script

    @script
    def hello_script():
        return "echo 'Hello, World!'"


This will return a :class:`quickie.tasks.Script` instance, equivalent to:

.. code-block:: python

    from quickie import Script

    class HelloScript(Script):
        def get_script(self):
            return "echo 'Hello, World!'"


Command Tasks
-------------

Command tasks run subprocesses.
The simplest way is to use :func:`quickie.command` decorator to define a task:

.. code-block:: python

    from quickie import command

    @command
    def some_command():
        return ["my_command", "arg1", "arg2"]

This will return a :class:`quickie.tasks.Command` instance, equivalent to:

.. code-block:: python

    from quickie import Command

    class SomeCommand(Command):
        def get_cmd(self):
            return ["my_command", "arg1", "arg2"]


GroupTasks
----------

Group tasks are used to run multiple tasks in order.

The simplest way is to use the :func:`quickie.group` decorator to define a group task:

.. code-block:: python

    from quickie import group

    @task
    def task1():
        print("Task 1")

    @task
    def task2():
        print("Task 2")

    @group
    def my_group():
        return [
            task1,
            task2,
        ]


This will return a :class:`quickie.tasks.Group` instance, equivalent to:

.. code-block:: python

    from quickie import Group

    class MyGroup(Group):
        def get_tasks(self):
            return [
                task1,
                task2,
            ]


ThreadGroupTasks
----------------

Thread group tasks are used to run multiple tasks in parallel.

The simplest way is to use the :func:`quickie.thread_group` decorator to define a thread group task:

.. code-block:: python

    from quickie import thread_group

    @task
    def task1():
        print("Task 1")

    @task
    def task2():
        print("Task 2")

    @thread_group
    def my_thread_group():
        return [
            task1,
            task2,
        ]


This will return a :class:`quickie.tasks.ThreadGroup` instance, equivalent to:

.. code-block:: python

    from quickie import ThreadGroup

    class MyThreadGroup(ThreadGroup):
        def get_tasks(self):
            return [
                task1,
                task2,
            ]


Changing the task name
----------------------

By default the task name is the function/class name. You can change the task name, or add aliases, by passing the `name` argument to the task decorator.

.. code-block:: python

    from quickie import task

    @task(name="my_task")
    def task1():
        print("Task 1")

    @task(name=["task2", "t2"])
    def task2():
        print("Task 2")

    # This will run task1
    qck my_task

    # These will run task2
    qck task2
    qck t2


Equivalent to:

.. code-block:: python

    from quickie import Task

    class MyTask(Task, name="my_task"):
        pass

    class Task2(Task, name=["task2", "t2"]):
        pass


Arguments
---------

You can define arguments for your tasks using the :func:`quickie.arg` decorator.
This will add the argument to the task's signature and make it available as a keyword argument.
In addition, you can pass `extra_args=True` to the task decorator to allow unknown arguments to be passed to the task.

.. code-block:: python

    from quickie import arg, task

    @task
    @arg("--name", help="Your name")
    def hello(name):
        print(f"Hello, {name}!")

    @task(extra_args=True)
    @arg("--flag", help="A flag", action="store_true")
    def hello_extra(*args, flag=False):
        print(f"{args=}, {flag=}")

Under the hood each Task defines an `argparse.ArgumentParser <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser>`_ instance.
By using the `arg` decorator we call the `argparse.ArgumentParser.add_argument <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument>`_
method with the provided arguments. The exception is the `completer` argument, which is used for :doc:`auto completion <how_tos/task_autocompletion>`.

Please refer to
`argparse.ArgumentParser.add_argument <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument>`_
for more information on the available arguments.


Conditions
----------

Conditions are used to determine if a task should run or not. They can be chained together with logical operators to create complex conditions.

Logical operators:

- `&` for AND
- `|` for OR
- `~` for NOT
- `^` for XOR

.. code-block:: python

    from quickie import task, conditions

    @task(condition[conditions.FirstRun() & conditions.PathsExist("file1", "file2"))
    def some_task():
        print("This task will run only the first time and if both files exist.")


You can use built-in conditions from :mod:`quickie.conditions` or create your own by subclassing :class:`quickie.conditions.base.BaseCondition` and
implementing the :meth:`quickie.conditions.base.BaseCondition.__call__` method, which should return ``True`` if the condition passes, ``False`` otherwise.
Additionally the :meth:`quickie.conditions.base.BaseCondition.__call__` must accept the task as an argument, and the arguments passed to the task.

Additionally you can use the :func:`quickie.conditions.condition` decorator to create a condition from a function.


Private tasks
-------------

You can define private tasks by prefixing the task name with an underscore.

.. code-block:: python

    from quickie import task

    @task
    def _private_task():
        print("Private task")


Roughly equivalent to:

.. code-block:: python

    from quickie import Task

    class _PrivateTask(Task):
        def run(self):
            print("Private task")


Sometimes however, it is useful to create base task classes that are not meant to be run directly.
This can be achieved by setting `private=True` when defining the class.

.. code-block:: python

    from quickie import Task

    class BaseTask(Task, private=True):
        pass
