Task Inheritance
================

Sometimes you want to create a task that is a slight variation of another task.
You can do this by inheriting from the original task and overriding the parts
you want to change.

Here is an example:

.. code-block:: python

    from quickie import task

    class MyTask(task.Task):
        def run(self):
            print("Hello, world!")

    class MyTaskWithArgs(MyTask):
        def run(self):
            print(f"Hello, {self.args.name}!")


Because factory methods such as :meth:`quickie.task` and :meth:`quickie.script` return a class, you can use inheritance with them as well:

.. code-block:: python

    from quickie import task, name

    @script
    @arg("name", help="The name to greet")
    def hello(name):
        return """echo "Hello, {name}!""""

    class greet_and_goodbye(hello):
        def get_script(self, name):
            return f"{super().get_script()}\necho 'Goodbye, {name}!'"
