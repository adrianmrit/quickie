'''Factories for creating tasks from functions.

We can create tasks from functions using the `task`, `script`, and `command`
decorators. Additionally, we can add arguments to the tasks using the `arg`
decorator.

.. code-block:: python

    @task(
        name="hello"
        args=[
            Arg("number1", type=int, help="The first number."),
            Arg("number2", type=int, help="The second number."),
        ]
    )
    def sum(number1, number2):
        console.print(f"The sum is {number1 + number2}.")

    @script(args=["--name"])
    def sum(name="world"):
        """Docstring will be used as help text."""
        return f"echo Hello, {name}!"

    @command
    def compose():
        return ["docker", "compose", "up"]
'''

import functools
import typing

from quickie import tasks
from quickie.utils.argparser import Arg


# This class is used as a convenience for custom factories, and should be in sync with
# the task decorator. Some params, i.e. for base classes are excluded, as they would not
# be usually used in the custom factory.
class CommonTaskKwargs(typing.TypedDict, total=False):
    """Common keyword arguments for task decorators."""

    name: str | None
    aliases: typing.Sequence[str] | None
    private: bool
    args: typing.Sequence[Arg | str | typing.Sequence[str]] | None
    extra_args: bool | None
    bind: bool
    condition: tasks.BaseCondition | None
    before: typing.Sequence[typing.Callable] | None
    after: typing.Sequence[typing.Callable] | None
    cleanup: typing.Sequence[typing.Callable] | None


type PartialReturnType[T: tasks.Task] = typing.Callable[[typing.Callable | type[T]], T]
"""Used for type hinting the return type of a decorator.

PartialReturnType is used for when the decorator function is called, returning a
new decorator function that will take the actual decorated function as an argument.
"""

type DecoratorReturnType[T: tasks.Task] = T | PartialReturnType[T]
"""Used for type hinting the return type of a decorator.

This is a general type hint for the decorator function, which can either return a
decorated class or a partial function that will take the decorated function as an
argument.
"""


@typing.overload
def task_factory_helper[T: tasks.Task](
    obj: typing.Callable | type[T],
    *,
    base: type[T],
    override_method: str,
) -> T: ...


@typing.overload
def task_factory_helper[T: tasks.Task](
    obj: typing.Callable | type[T],
    *,
    name: str | None,
    aliases: typing.Sequence[str] | None = None,
    private: bool = False,
    args: typing.Sequence[Arg | str | typing.Sequence[str]] | None = None,
    extra_args: bool | None,
    bind: bool,
    condition: tasks.BaseCondition | None,
    before: typing.Sequence[typing.Callable] | None,
    after: typing.Sequence[typing.Callable] | None,
    cleanup: typing.Sequence[typing.Callable] | None,
    base: type[T],
    override_method: str,
    attrs: dict[str, typing.Any] | None = None,
    kwargs: dict[str, typing.Any] | None = None,
) -> T: ...


@typing.overload
def task_factory_helper[T: tasks.Task](
    obj: None = None,
    *,
    private: bool = False,
    base: type[T],
    override_method: str,
    attrs: dict[str, typing.Any] | None = None,
    kwargs: dict[str, typing.Any] | None = None,
    args: typing.Sequence[Arg | str | typing.Sequence[str]] | None = None,
    extra_args: bool | None,
    bind: bool,
    condition: tasks.BaseCondition | None,
    before: typing.Sequence[typing.Callable] | None,
    after: typing.Sequence[typing.Callable] | None,
    cleanup: typing.Sequence[typing.Callable] | None,
) -> PartialReturnType[T]: ...


@typing.overload
def task_factory_helper[T: tasks.Task](
    obj: typing.Callable | type[T] | None = None,
    *,
    name: str | None = None,
    aliases: typing.Sequence[str] | None = None,
    private: bool = False,
    args: typing.Sequence[Arg | str | typing.Sequence[str]] | None = None,
    extra_args: bool | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[typing.Callable] | None = None,
    after: typing.Sequence[typing.Callable] | None = None,
    cleanup: typing.Sequence[typing.Callable] | None = None,
    base: type[T],
    override_method: str,
    attrs: dict[str, typing.Any] | None = None,
    kwargs: dict[str, typing.Any] | None = None,
) -> DecoratorReturnType[T]:
    pass


def task_factory_helper[  # noqa: PLR0913 PLR0912
    T: tasks.Task
](
    obj: typing.Callable | type[T] | None = None,
    *,
    name: str | None = None,
    aliases: typing.Sequence[str] | None = None,
    private: bool = False,
    args: typing.Sequence[Arg | str | typing.Sequence[str]] | None = None,
    extra_args: bool | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[typing.Callable] | None = None,
    after: typing.Sequence[typing.Callable] | None = None,
    cleanup: typing.Sequence[typing.Callable] | None = None,
    base: type[T],
    override_method: str,
    attrs: dict[str, typing.Any] | None = None,
    kwargs: dict[str, typing.Any] | None = None,
) -> DecoratorReturnType[T]:
    '''Create a task class from a function.

    You might find this useful when you have a base class for tasks and you want to
    create your own decorator that creates tasks from functions.

    Other decorators like :func:`task`, :func:`script`, and :func:`command` use this
    function internally.

    .. code-block:: python

        class MyModuleTask(tasks.Command):
            def get_binary(self):
                return "python"

            def get_extra_cmd_args(self):
                raise NotImplementedError

            def get_cmd_args(self):
                return ["-m", "my_module", self.get_extra_cmd_args()]

        def module_task(obj=None, **kwargs):
            return generic_task(
                obj,
                base=MyModuleTask,
                override_method=tasks.Command.get_extra_cmd_args.__name__,
                **kwargs,
            )

        @module_task(name="hello")
        def hello_module_task(task):
            """"Run my_module with 'hello' argument."""
            return ["hello"]


    :param obj: The function to create the task from. If None, a partial
        function will be returned, so you can use this function as a decorator
        with the arguments.
    :param name: The name of the task.
    :param aliases: The aliases of the task.
    :param private: If true, the task is private and will not be shown in the
    :param args: The arguments for the task. Can pass `Arg` objects, but also
        strings or tuples of strings that will be used as a shortcut for the
        `Arg` object. For example, `args=["--arg1", ("--name", "-n")]` is equivalent to
        `args=[Arg("--arg1"), Arg("--name", "-n")]`.
    :param extra_args: If the task accepts extra arguments.
    :param bind: If true, the first parameter of the function will be the
        task class instance.
    :param condition: The condition to check before running the task.
    :param before: The tasks to run before the task.
    :param after: The tasks to run after the task.
    :param cleanup: The tasks to run after the task, even if it fails.
    :param base: The base class for the task.
    :param override_method: The method to override in the task.
    :param attrs: Extra attributes for the task class. Ignored if `obj` is a
        class.
    :param kwargs: Extra keyword arguments to initialize the task.

    :returns: The task class, or, if `obj` is None, a partial function to be
        used as a decorator for a function.
    '''
    if obj is None:
        return functools.partial(
            task_factory_helper,
            name=name,
            aliases=aliases,
            args=args,
            extra_args=extra_args,
            bind=bind,
            condition=condition,
            before=before,
            after=after,
            cleanup=cleanup,
            base=base,
            override_method=override_method,
            attrs=attrs,
            kwargs=kwargs,
            private=private,
        )

    if isinstance(obj, type):
        if not issubclass(obj, base):
            raise TypeError(f"obj must be a subclass of {base}")
        # bind and attrs are ignored
        cls = obj
    else:
        if bind:
            new_fn = functools.partialmethod(obj)  # type: ignore
        else:
            # Still wrap as a method
            def new_fn(_, *args, **kwargs):
                return obj(*args, **kwargs)

        attrs = {**attrs} if attrs else {}
        attrs[override_method] = new_fn

        cls = typing.cast(type[T], type(obj.__name__, (base,), attrs))
    return cls(
        name=name,
        aliases=aliases,
        defined_from=obj,
        private=private,
        args=args,
        extra_args=extra_args,
        condition=condition,
        before=before,
        after=after,
        cleanup=cleanup,
        **(kwargs or {}),
    )


@typing.overload
def task(
    obj: typing.Callable,
) -> tasks.Task: ...


@typing.overload
def task(
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> PartialReturnType[tasks.Task]: ...


def task(  # noqa: PLR0913
    obj: typing.Callable | None = None,
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> DecoratorReturnType[tasks.Task]:
    '''Create a task from a function.

    .. code-block:: python

        @task(name="hello")
        def hello_task():
            console.print("Hello, task!")

        @task
        def hello_world():
            """Docstring will be used as help text."""
            print("Hello, world!")

    :param obj: The function to create the task from.
    :param kwargs: Common keyword arguments for tasks. See `CommonTaskKwargs` for more
        information.

    :returns: The task class, or, if `obj` is None, a partial function to be
        used as a decorator for a function.
    '''
    return task_factory_helper(
        obj,
        **kwargs,
        base=tasks.Task,
        override_method=tasks.Task.run.__name__,
    )


@typing.overload
def script(
    obj: typing.Callable[..., str],
) -> tasks.Script: ...


@typing.overload
def script(
    *,
    executable: str | None = None,
    env: dict[str, str] | None = None,
    wd: str | None = None,
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> PartialReturnType[tasks.Script]: ...


def script(  # noqa: PLR0913
    obj: typing.Callable[..., str] | None = None,
    *,
    executable: str | None = None,
    env: dict[str, str] | None = None,
    wd: str | None = None,
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> DecoratorReturnType[tasks.Script]:
    '''Create a script from a function.

    .. code-block:: python

        @script(name="hello", bind=True)
        def hello_script(task):
            return "echo Hello, script!"

        @script
        def hello_world():
            """Docstring will be used as help text."""
            return "echo Hello, world!"

    :param obj: The function to create the script from.
    :param executable: The executable to use for the script.
    :param env: The environment variables for the script.
    :param wd: The working directory for the script.
    :param kwargs: Common keyword arguments for tasks. See `CommonTaskKwargs` for more
        information.

    :returns: The task class, or, if `obj` is None, a partial function to be
        used as a decorator for a function.
    '''
    attrs = {"executable": executable, "env": env, "wd": wd}
    return task_factory_helper(
        obj,
        base=tasks.Script,
        override_method=tasks.Script.get_script.__name__,
        attrs=attrs,
        kwargs=attrs,
        **kwargs,
    )


@typing.overload
def command(
    obj: typing.Callable[..., typing.Sequence[str] | str],
) -> tasks.Command: ...


@typing.overload
def command(
    *,
    env: dict[str, str] | None = None,
    wd: str | None = None,
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> PartialReturnType[tasks.Command]: ...


def command(  # noqa: PLR0913
    obj: typing.Callable[..., typing.Sequence[str]] | None = None,
    *,
    env: dict[str, str] | None = None,
    wd: str | None = None,
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> DecoratorReturnType[tasks.Command]:
    '''Create a command task from a function.

    .. code-block:: python

        @command(name="hello", bind=True)
        def run_program(task):
            return ["program", "arg1", "arg2"]

        @command
        def hello_world():
            """Docstring will be used as help text."""
            return ["program", "arg1", "arg2"]

    :param obj: The function to create the command task from.
    :param kwargs: Common keyword arguments for tasks. See `CommonTaskKwargs` for more
        information.
    :param env: The environment variables for the command task.
    :param wd: The working directory for the command task.

    :returns: The command task class, or, if `obj` is None, a partial function to be
        used as a decorator for a function.
    '''
    attrs = {"env": env, "wd": wd}
    return task_factory_helper(
        obj,
        base=tasks.Command,
        override_method=tasks.Command.get_cmd.__name__,
        attrs=attrs,
        kwargs=attrs,
        **kwargs,
    )


@typing.overload
def group(
    obj: typing.Callable,
) -> tasks.Group: ...


@typing.overload
def group(  # noqa: PLR0913
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> PartialReturnType[tasks.Group]: ...


def group(  # noqa: PLR0913
    obj: typing.Callable | None = None,
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> DecoratorReturnType[tasks.Group]:
    """Create a group task from a function.

    The returned task will run in the same order without extra arguments.
    To add arguments to individual tasks in the group, you can use
    :func:`functools.partial`.

    .. code-block:: python

        @group(args=["arg1"])
        def my_group(arg1):
            return [task1, functools.partial(task2, arg1)]

    :param obj: The function to create the group task from.
    :param kwargs: Common keyword arguments for tasks. See `CommonTaskKwargs` for more
        information.

    :returns: The group task class, or, if `obj` is None, a partial function to be
        used as a decorator for a function.
    """
    return task_factory_helper(
        obj,
        base=tasks.Group,
        override_method=tasks.Group.get_tasks.__name__,
        **kwargs,
    )


@typing.overload
def thread_group(
    obj: typing.Callable,
) -> tasks.ThreadGroup: ...


@typing.overload
def thread_group(
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> PartialReturnType[tasks.ThreadGroup]: ...


def thread_group(  # noqa: PLR0913
    obj: typing.Callable | None = None,
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> DecoratorReturnType[tasks.ThreadGroup]:
    """Create a thread group task from a function.

    The returned task will run in parallel. To add arguments to individual tasks
    in the group, you can use `functools.partial` with the task and the
    arguments.

    Note that the tasks run in separate threads, so they should be thread-safe. This
    means that they are also affected by the Global Interpreter Lock (GIL).

    .. code-block:: python

        @thread_group(args=["arg1"])
        def my_group(arg1):
            return [task1, functools.partial(task2, arg1)]

    :param obj: The function to create the thread group task from.
    :param kwargs: Common keyword arguments for tasks. See `CommonTaskKwargs` for more
        information.

    :returns: The thread group task class, or, if `obj` is None, a partial function to
        be used as a decorator for a function.
    """
    return task_factory_helper(
        obj,
        base=tasks.ThreadGroup,
        override_method=tasks.ThreadGroup.get_tasks.__name__,
        **kwargs,
    )
