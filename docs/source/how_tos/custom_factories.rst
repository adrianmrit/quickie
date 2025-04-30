Custom Factories
================

Quickie provides a way to create custom factories for your tasks. This allows you to create tasks that are tailored to your specific needs,
and to reuse code across multiple tasks.

To make the creation of custom factories easier, Quickie provides the `generic_task_factory` function. This function takes care of the
boilerplate code for you, and allows you to create a custom factory with just a few lines of code.

In the following example we have taken care of adding type hints, but you can skip this step if you don't need them.

.. code-block:: python

    import typing as t
    from quickie.tasks import Command
    from quickie.factories import generic_task_factory, PartialReturnType, CommonTaskKwargs

    @t.overload
    def git(fn: t.Callable) -> type[Git]:
        ...

    @t.overload
    def git(fn: None = None, **kwargs: typing.Unpack[CommonTaskKwargs]) -> PartialReturnType[Git]:
        ...

    def git(fn: t.Callable | None = None, **kwargs: typing.Unpack[CommonTaskKwargs]):
        return generic_task_factory(
            fn,
            # Base classes for the task. Could be a custom class
            bases=(Command,),
            # Overrides the method such that it returns the result of the decorated function
            override_method="get_args",
            # Extra attributes to add to the task
            attrs={"binary": "git"},
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
    from quickie.factories import generic_task_factory

    def git(fn=None, **kwargs):
        return generic_task_factory(
            fn,
            bases=(Command,),
            override_method="get_args",
            attrs={"binary": "git"},
            **kwargs,
        )

    @git
    def _push(self, args):
        return ["push", *args]

    @git(name="commitp", after=[_push], extra_args=True)
    def commit_and_push(*args):
        return ["commit", *args]
