Accepting arguments
===================

You can define arguments for your tasks using the :func:`quickie.arg` decorator.
This will add the argument to the task's signature and make it available as a keyword argument.
In addition, you can pass `extra_args=True` to the task decorator to allow unknown arguments to be passed to the task.

.. code-block:: python

    from quickie import arg, task

    @task
    @arg("--name", help="Your name")
    def hello(name):
        print(f"Hello, {name}!")

    # Order does not matter
    @arg("--flag", help="A flag", action="store_true")
    @task(extra_args=True)
    def hello_extra(*args, flag=False):
        print(f"{args=}, {flag=}")

    @arg("--number", help="A number", type=int)
    class MyTask(task.Task):
        def run(self, number):
            print(f"Number: {self.args.number}")

Under the hood each Task defines an `argparse.ArgumentParser <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser>`_ instance.
By using the `arg` decorator we call the `argparse.ArgumentParser.add_argument <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument>`_
method with the provided arguments. The exception is the `completer` argument, which is used for :doc:`auto completion <how_tos/task_autocompletion>`.

This should be enough for most use cases, but you can still override the `add_args` method in your Task class to add more
complex argument parsing logic.

.. code-block:: python

    from quickie import task

    class MyTask(task.Task):
        def add_args(self, parser):
            parser.add_argument("--name", help="Your name")

        def run(self):
            print(f"Hello, {self.args.name}!")

Please refer to
`argparse.ArgumentParser.add_argument <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument>`_
for more information on the available arguments.

Accepting unknown arguments
---------------------------

By default, tasks will raise an error if unknown arguments are passed to them. We can change this behavior by passing `extra_args=True` to the task decorator,
or setting it as a class attribute.

.. code-block:: python

    from quickie import task

    @task(extra_args=True)
    def my_task(*args, **kwargs):
        print(f"{args=}, {kwargs=}")

    class MyTask(task.Task):
        extra_args = True

        def run(self, *args, **kwargs):
            print(f"{args=}, {kwargs=}")


This will allow any arguments to be passed to the task, and they will be available as positional arguments (`args` in the example).
