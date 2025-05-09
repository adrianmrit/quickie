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
from quickie.tasks import TaskTypeOrProxy
from quickie.utils.argparser import Arg


# This class is used as a convenience for custom factories, and should be in sync with
# the task decorator. Some params, i.e. for base classes are excluded, as they would not
# be usually used in the custom factory.
class CommonTaskKwargs(typing.TypedDict, total=False):
    """Common keyword arguments for task decorators."""

    name: str | None
    aliases: typing.Sequence[str] | None
    private: bool | None
    args: typing.Sequence[Arg | str | typing.Sequence[str]] | None
    extra_args: bool | None
    bind: bool
    condition: tasks.BaseCondition | None
    before: typing.Sequence["TaskTypeOrProxy"] | None
    after: typing.Sequence["TaskTypeOrProxy"] | None
    cleanup: typing.Sequence["TaskTypeOrProxy"] | None


type PartialReturnType[T: tasks.Task] = typing.Callable[[typing.Callable], type[T]]
"""Used for type hinting the return type of a decorator.

PartialReturnType is used for when the decorator function is called, returning a
new decorator function that will take the actual decorated function as an argument.
"""

type DecoratorReturnType[T: tasks.Task] = type[T] | PartialReturnType[T]
"""Used for type hinting the return type of a decorator.

This is a general type hint for the decorator function, which can either return a
decorated class or a partial function that will take the decorated function as an
argument.
"""


@typing.overload
def generic_task_factory[T: tasks.Task](
    fn: typing.Callable,
    *,
    bases: tuple[type[T], ...],
    override_method: str,
) -> type[T]: ...


@typing.overload
def generic_task_factory[T: tasks.Task](
    fn: typing.Callable,
    *,
    name: str | None,
    aliases: typing.Sequence[str] | None = None,
    private: bool | None = None,
    args: typing.Sequence[Arg | str | typing.Sequence[str]] | None = None,
    extra_args: bool | None,
    bind: bool,
    condition: tasks.BaseCondition | None,
    before: typing.Sequence["TaskTypeOrProxy"] | None,
    after: typing.Sequence["TaskTypeOrProxy"] | None,
    cleanup: typing.Sequence["TaskTypeOrProxy"] | None,
    bases: tuple[type[T], ...],
    override_method: str,
    attrs: dict[str, typing.Any] | None = None,
) -> type[T]: ...


@typing.overload
def generic_task_factory[T: tasks.Task](
    fn: None = None,
    *,
    private: bool | None = None,
    bases: tuple[type[T], ...],
    override_method: str,
    attrs: dict[str, typing.Any] | None = None,
    args: typing.Sequence[Arg | str | typing.Sequence[str]] | None = None,
    extra_args: bool | None,
    bind: bool,
    condition: tasks.BaseCondition | None,
    before: typing.Sequence["TaskTypeOrProxy"] | None,
    after: typing.Sequence["TaskTypeOrProxy"] | None,
    cleanup: typing.Sequence["TaskTypeOrProxy"] | None,
) -> PartialReturnType[T]: ...


@typing.overload
def generic_task_factory[T: tasks.Task](
    fn: typing.Callable | None = None,
    *,
    name: str | None = None,
    aliases: typing.Sequence[str] | None = None,
    private: bool | None = None,
    args: typing.Sequence[Arg | str | typing.Sequence[str]] | None = None,
    extra_args: bool | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence["TaskTypeOrProxy"] | None = None,
    after: typing.Sequence["TaskTypeOrProxy"] | None = None,
    cleanup: typing.Sequence["TaskTypeOrProxy"] | None = None,
    bases: tuple[type[T], ...],
    override_method: str,
    attrs: dict[str, typing.Any] | None = None,
) -> DecoratorReturnType[T]:
    pass


def generic_task_factory[  # noqa: PLR0913
    T: tasks.Task
](
    fn: typing.Callable | None = None,
    *,
    name: str | None = None,
    aliases: typing.Sequence[str] | None = None,
    private: bool | None = None,
    args: typing.Sequence[Arg | str | typing.Sequence[str]] | None = None,
    extra_args: bool | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence["TaskTypeOrProxy"] | None = None,
    after: typing.Sequence["TaskTypeOrProxy"] | None = None,
    cleanup: typing.Sequence["TaskTypeOrProxy"] | None = None,
    bases: tuple[type[T], ...],
    override_method: str,
    attrs: dict[str, typing.Any] | None = None,
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

        def module_task(fn=None, **kwargs):
            return generic_task(
                fn,
                bases=(MyModuleTask,),
                override_method=tasks.Command.get_extra_cmd_args.__name__,
                **kwargs,
            )

        @module_task(name="hello")
        def hello_module_task(task):
            """"Run my_module with 'hello' argument."""
            return ["hello"]


    :param fn: The function to create the task from. If None, a partial
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
    :param bases: The base classes for the task.
    :param override_method: The method to override in the task.
    :param attrs: Extra keyword arguments for the task class.

    :returns: The task class, or, if `fn` is None, a partial function to be
        used as a decorator for a function.
    '''
    if fn is None:
        return functools.partial(
            generic_task_factory,
            name=name,
            aliases=aliases,
            args=args,
            extra_args=extra_args,
            bind=bind,
            condition=condition,
            before=before,
            after=after,
            cleanup=cleanup,
            bases=bases,
            override_method=override_method,
            attrs=attrs,
            private=private,
        )

    kwds: dict[str, typing.Any] = {}
    if attrs is not None:
        kwds.update(attrs)

    if args is not None:  # inherited otherwise
        kwds["args"] = args

    if extra_args is not None:  # inherited otherwise
        kwds["extra_args"] = extra_args

    if condition:
        kwds["condition"] = condition

    if before:
        kwds["before"] = before

    if after:
        kwds["after"] = after

    if cleanup:
        kwds["cleanup"] = cleanup

    if bind:
        new_fn = functools.partialmethod(fn)  # type: ignore
    else:
        # Still wrap as a method
        def new_fn(_, *args, **kwargs):
            return fn(*args, **kwargs)

    kwds[override_method] = new_fn

    return tasks._TaskMeta(
        fn.__name__,
        bases,
        kwds,
        name=name,
        aliases=aliases,
        defined_from=fn,
        private=private,
    )  # type: ignore


@typing.overload
def task(
    fn: typing.Callable,
) -> type[tasks.Task]: ...


@typing.overload
def task(
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> PartialReturnType[tasks.Task]: ...


def task(  # noqa: PLR0913
    fn: typing.Callable | None = None,
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

    :param fn: The function to create the task from.
    :param kwargs: Common keyword arguments for tasks. See `CommonTaskKwargs` for more
        information.

    :returns: The task class, or, if `fn` is None, a partial function to be
        used as a decorator for a function.
    '''
    return generic_task_factory(
        fn,
        **kwargs,
        bases=(tasks.Task,),
        override_method=tasks.Task.run.__name__,
    )


@typing.overload
def script(
    fn: typing.Callable[..., str],
) -> type[tasks.Script]: ...


@typing.overload
def script(
    *,
    executable: str | None = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> PartialReturnType[tasks.Script]: ...


def script(  # noqa: PLR0913
    fn: typing.Callable[..., str] | None = None,
    *,
    executable: str | None = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
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

    :param fn: The function to create the script from.
    :param executable: The executable to use for the script.
    :param env: The environment variables for the script.
    :param cwd: The working directory for the script.
    :param kwargs: Common keyword arguments for tasks. See `CommonTaskKwargs` for more
        information.

    :returns: The task class, or, if `fn` is None, a partial function to be
        used as a decorator for a function.
    '''
    return generic_task_factory(
        fn,
        bases=(tasks.Script,),
        override_method=tasks.Script.get_script.__name__,
        attrs={"env": env, "cwd": cwd, "executable": executable},
        **kwargs,
    )


@typing.overload
def command(
    fn: typing.Callable[..., typing.Sequence[str] | str],
) -> type[tasks.Command]: ...


@typing.overload
def command(
    *,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> PartialReturnType[tasks.Command]: ...


def command(  # noqa: PLR0913
    fn: typing.Callable[..., typing.Sequence[str]] | None = None,
    *,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
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

    :param fn: The function to create the command task from.
    :param kwargs: Common keyword arguments for tasks. See `CommonTaskKwargs` for more
        information.
    :param env: The environment variables for the command task.
    :param cwd: The working directory for the command task.

    :returns: The command task class, or, if `fn` is None, a partial function to be
        used as a decorator for a function.
    '''
    return generic_task_factory(
        fn,
        bases=(tasks.Command,),
        override_method=tasks.Command.get_cmd.__name__,
        attrs={"env": env, "cwd": cwd},
        **kwargs,
    )


@typing.overload
def group(
    fn: typing.Callable,
) -> type[tasks.Group]: ...


@typing.overload
def group(  # noqa: PLR0913
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> PartialReturnType[tasks.Group]: ...


def group(  # noqa: PLR0913
    fn: typing.Callable | None = None,
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> DecoratorReturnType[tasks.Group]:
    """Create a group task from a function.

    The returned task will run in the same order without extra arguments.
    To add arguments to individual tasks in the group, you can use
    :func:`partial_task`.

    .. code-block:: python

        @group(args=["arg1"])
        def my_group(arg1):
            return [task1, partial_task(task2, arg1)]

    :param fn: The function to create the group task from.
    :param kwargs: Common keyword arguments for tasks. See `CommonTaskKwargs` for more
        information.

    :returns: The group task class, or, if `fn` is None, a partial function to be
        used as a decorator for a function.
    """
    return generic_task_factory(
        fn,
        bases=(tasks.Group,),
        override_method=tasks.Group.get_tasks.__name__,
        **kwargs,
    )


@typing.overload
def thread_group(
    fn: typing.Callable,
) -> type[tasks.ThreadGroup]: ...


@typing.overload
def thread_group(
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> PartialReturnType[tasks.ThreadGroup]: ...


def thread_group(  # noqa: PLR0913
    fn: typing.Callable | None = None,
    **kwargs: typing.Unpack[CommonTaskKwargs],
) -> DecoratorReturnType[tasks.ThreadGroup]:
    """Create a thread group task from a function.

    The returned task will run in parallel. To add arguments to individual tasks
    in the group, you can return an instance of `partial_task` with the task and the
    arguments.

    Note that the tasks run in separate threads, so they should be thread-safe. This
    means that they are also affected by the Global Interpreter Lock (GIL).

    .. code-block:: python

        @thread_group(args=["arg1"])
        def my_group(arg1):
            return [task1, partial_task(task2, arg1)]

    :param fn: The function to create the thread group task from.
    :param kwargs: Common keyword arguments for tasks. See `CommonTaskKwargs` for more
        information.

    :returns: The thread group task class, or, if `fn` is None, a partial function to
        be used as a decorator for a function.
    """
    return generic_task_factory(
        fn,
        bases=(tasks.ThreadGroup,),
        override_method=tasks.ThreadGroup.get_tasks.__name__,
        **kwargs,
    )
