Lazy task references
====================

In some places you might need to define a task lazily. For example `before`, `after`, and `cleanup` tasks can reference tasks by name. Under the hood this
will create a `lazy_task` that will be resolved when the task is run.

For example the following are equivalent:

.. code-block:: python

    from quickie import task

    @task
    def task1():
        print("Task 1")

    @task(after=["task1"])
    def task2():
        print("Task 2")

    @task(after=[lazy_task("task1")])
    def task2():
        print("Task 2")


Lazy tasks will simply load the appropriate task when you try to initialize them. It will do so by using the context passed to the task.

.. code-block:: python

    from quickie import task, lazy_task

    @task
    def task1():
        print("Task 1")

    @task(bind=True)
    def task2(self):
        task1_reference = lazy_task("task1")
        task1_instance = task1_reference(context=self.context)
        task1_instance.run()
        print("Task 2")

    # Calling task2 will print:
    # This will print:
    # Task 1
    # Task 2
