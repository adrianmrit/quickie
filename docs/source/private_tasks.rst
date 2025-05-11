Private tasks
=============

Sometimes you want to define tasks that are not meant to be run directly, but rather from other tasks. You can use
simple functions most of the time, but sometimes it is useful to define them as tasks. This can be achieved by
passing the `private=True` argument to the task decorator.

.. code-block:: python

    from quickie import task

    @task(private=True)
    def private_task():
        print("Private task")

    # We can avoid avoid writing the logic to run the script
    @script(private=True)
    def private_command():
        return "echo 'Private command'"
