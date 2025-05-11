Custom Factories
================

Quickie provides a way to create custom factories for your tasks. This allows you to create tasks that are tailored to your specific needs,
and to reuse code across multiple tasks.

To make the creation of custom factories easier, Quickie provides the `task_factory_helper` function. This function takes care of the
boilerplate code for you, and allows you to create a custom factory with just a few lines of code.

In the following example we have taken care of adding type hints, but you can skip this step if you don't need them.

.. code-block:: python

    import typing as t
    from quickie.tasks import Command
    from quickie.factories import task_factory_helper, PartialReturnType, CommonTaskKwargs

    @t.overload
    def git(obj: t.Callable | type) -> type[Command]:
        ...

    @t.overload
    def git(obj: None = None, **kwargs: typing.Unpack[CommonTaskKwargs]) -> PartialReturnType[Command]:
        ...

    def git(obj: t.Callable | type | None = None, **kwargs: typing.Unpack[CommonTaskKwargs]):
        return task_factory_helper(
            obj,
            # Base class for the task.
            base=Command,
            # Overrides the method such that it returns the result of the decorated function
            override_method="get_cmd_args",
            # Keyword arguments to pass to the task during initialization.
            kwargs={"binary": "git"}
            **kwargs
        )

    @git
    def _push(self, args):
        return ["push", *args]

    @git(name="commitp", after=[_push], extra_args=True)
    def commit_and_push(*args):
        return ["commit", *args]


Without the type hints, the code would look like this:

.. code-block:: python

    from quickie.tasks import Command
    from quickie.factories import task_factory_helper

    def git(fn=None, **kwargs):
        return task_factory_helper(
            fn,
            base=Command,
            override_method="get_cmd_args",
            kwargs={"binary": "git"},
            **kwargs,
        )

    @git
    def push(self, args):
        return ["push", *args]

    @git(name="commitp", after=[push], extra_args=True)
    def commit_and_push(*args):
        return ["commit", *args]
