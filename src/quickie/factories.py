'''Factories for creating tasks from functions.

We can create tasks from functions using the `task`, `script`, and `command`
decorators. Additionally, we can add arguments to the tasks using the `arg`
decorator.

.. code-block:: python

    @task(name="hello", bind=True)
    @arg("number1", type=int, help="The first number.")
    @arg("number2", type=int, help="The second number.")
    def sum(task, number1, number2):
        task.console.print(f"The sum is {number1 + number2}.")

    @script
    @arg("--name", help="The name to greet.")
    def sum(name="world"):
        """Docstring will be used as help text."""
        return f"echo Hello, {name}!"

    @command
    def compose():
        return ["docker", "compose", "up"]
'''

import functools
import typing
from argparse import Action, ArgumentParser

from quickie import tasks

if typing.TYPE_CHECKING:
    from quickie.tasks import TaskTypeOrProxy
else:
    TaskTypeOrProxy = typing.Any


class _OptionKwargs(typing.TypedDict, total=False):
    action: str | type[Action]
    nargs: int | str | None
    const: typing.Any
    default: typing.Any
    type: typing.Callable | None
    choices: typing.Iterable | None
    required: bool
    help: str | None
    metavar: str | tuple[str, ...]
    dest: str | None
    version: str


class _CommonTaskFactoryKwargs(typing.TypedDict):
    name: str | typing.Sequence[str] | None
    extra_args: bool | None
    bind: bool
    condition: tasks.BaseCondition | None
    before: typing.Sequence[TaskTypeOrProxy] | None
    after: typing.Sequence[TaskTypeOrProxy] | None
    cleanup: typing.Sequence[TaskTypeOrProxy] | None


type PartialReturnType[T: tasks.Task] = typing.Callable[[typing.Callable], type[T]]
type DecoratorReturnType[T: tasks.Task] = type[T] | PartialReturnType


def arg(
    *name_or_flags: str,
    completer: typing.Callable | None = None,
    **kwargs: typing.Unpack[_OptionKwargs],
):
    """Used to add arguments to the arguments parser of a task.

    Arguments are the same as the `add_argument` method of `argparse.ArgumentParser`,
    except for the `completer` argument which is a function that provides completion for
    the argument.

    :param name_or_flags: The name or flags for the argument.
    :param completer: A function to provide completion for the argument.
    :param kwargs: The keyword arguments for the argument. See `add_argument` method
        of `ArgumentParser` for more information.
    """

    def decorator(fn):
        if isinstance(fn, tasks._TaskMeta):
            fn = typing.cast(type[tasks.Task], fn)
            # decorator appears on top of a task decorator, or directly on top of a cls
            original_add_args = fn.add_args

            def add_args(self, parser: ArgumentParser):
                original_add_args(self, parser)
                parser.add_argument(*name_or_flags, **kwargs).completer = completer  # type: ignore

            return type(fn.__name__, (fn,), {"add_args": add_args})
        else:
            # Assume decorator appears before a task decorator
            if not hasattr(fn, "_options"):
                fn._options = []
            fn._options.append((name_or_flags, completer, kwargs))
            return fn

    return decorator


def _get_add_args_method(fn):
    if not hasattr(fn, "_options"):
        return None

    def add_args(self, parser: ArgumentParser):
        for name_or_flags, completer, kwargs in fn._options:
            parser.add_argument(*name_or_flags, **kwargs).completer = completer  # type: ignore

    return add_args


@typing.overload
def generic_task_factory[
    T: type[tasks.Task]
](fn: typing.Callable, *, bases: tuple[T, ...], override_method: str,) -> T:
    ...


@typing.overload
def generic_task_factory[
    T: tasks.Task
](
    fn: typing.Callable,
    *,
    bases: tuple[type[T], ...],
    override_method: str,
    extra_kwds: dict[str, typing.Any] | None = None,
    **kwargs: typing.Unpack[_CommonTaskFactoryKwargs],
) -> type[T]:
    ...


@typing.overload
def generic_task_factory[
    T: tasks.Task
](
    fn: None = None,
    *,
    bases: tuple[type[T], ...],
    override_method: str,
    extra_kwds: dict[str, typing.Any] | None = None,
    **kwargs: typing.Unpack[_CommonTaskFactoryKwargs],
) -> PartialReturnType[T]:
    ...


def generic_task_factory[  # noqa: PLR0913
    T: tasks.Task
](
    fn: typing.Callable | None = None,
    *,
    name: str | typing.Sequence[str] | None = None,
    extra_args: bool | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[TaskTypeOrProxy] | None = None,
    after: typing.Sequence[TaskTypeOrProxy] | None = None,
    cleanup: typing.Sequence[TaskTypeOrProxy] | None = None,
    bases: tuple[type[T], ...],
    override_method: str,
    extra_kwds: dict[str, typing.Any] | None = None,
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

            def get_extra_args(self):
                raise NotImplementedError

            def get_args(self):
                return ["-m", "my_module", self.get_extra_args()]

        def module_task(fn=None, **kwargs):
            return generic_task(
                fn,
                bases=(MyModuleTask,),
                override_method=tasks.Command.get_extra_args.__name__,
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
    :param extra_args: If the task accepts extra arguments.
    :param bind: If true, the first parameter of the function will be the
        task class instance.
    :param condition: The condition to check before running the task.
    :param before: The tasks to run before the task.
    :param after: The tasks to run after the task.
    :param cleanup: The tasks to run after the task, even if it fails.
    :param bases: The base classes for the task.
    :param override_method: The method to override in the task.
    :param extra_kwds: Extra keyword arguments for the task class.

    :returns: The task class, or, if `fn` is None, a partial function to be
        used as a decorator for a function.
    '''
    if fn is None:
        return functools.partial(  # type: ignore
            generic_task_factory,
            name=name,
            extra_args=extra_args,
            bind=bind,
            condition=condition,
            before=before,
            after=after,
            cleanup=cleanup,
            bases=bases,
            override_method=override_method,
            extra_kwds=extra_kwds,
        )

    kwds: dict[str, typing.Any] = {}
    if extra_kwds is not None:
        kwds.update(extra_kwds)

    add_args = _get_add_args_method(fn)
    if add_args is not None:
        kwds["add_args"] = add_args

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

    return tasks._TaskMeta(fn.__name__, bases, kwds, name=name)  # type: ignore


@typing.overload
def task(
    fn: typing.Callable,
) -> type[tasks.Task]:
    ...


@typing.overload
def task(
    *,
    name: str | None = None,
    extra_args: bool | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[TaskTypeOrProxy] | None = None,
    after: typing.Sequence[TaskTypeOrProxy] | None = None,
    cleanup: typing.Sequence[TaskTypeOrProxy] | None = None,
) -> PartialReturnType[tasks.Task]:
    ...


def task(  # noqa: PLR0913
    fn: typing.Callable | None = None,
    *,
    name: str | None = None,
    extra_args: bool | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[TaskTypeOrProxy] | None = None,
    after: typing.Sequence[TaskTypeOrProxy] | None = None,
    cleanup: typing.Sequence[TaskTypeOrProxy] | None = None,
) -> DecoratorReturnType[tasks.Task]:
    '''Create a task from a function.

    .. code-block:: python

        @task(name="hello", bind=True)
        def hello_task(task):
            task.console.print("Hello, task!")

        @task
        def hello_world():
            """Docstring will be used as help text."""
            print("Hello, world!")

    :param fn: The function to create the task from.
    :param name: The name of the task.
    :param extra_args: If the task accepts extra arguments.
    :param bind: If true, the first parameter of the function will be the
        task class instance.
    :param condition: The condition to check before running the task.
    :param before: The tasks to run before the task.
    :param after: The tasks to run after the task.
    :param cleanup: The tasks to run after the task, even if it fails.

    :returns: The task class, or, if `fn` is None, a partial function to be
        used as a decorator for a function.
    '''
    return generic_task_factory(
        fn,
        name=name,
        extra_args=extra_args,
        bind=bind,
        condition=condition,
        before=before,
        after=after,
        cleanup=cleanup,
        bases=(tasks.Task,),
        override_method=tasks.Task.run.__name__,
    )


@typing.overload
def script(
    fn: typing.Callable[..., str],
) -> type[tasks.Script]:
    ...


@typing.overload
def script(
    *,
    name: str | None = None,
    extra_args: bool | None = False,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[TaskTypeOrProxy] | None = None,
    after: typing.Sequence[TaskTypeOrProxy] | None = None,
    cleanup: typing.Sequence[TaskTypeOrProxy] | None = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
) -> PartialReturnType[tasks.Script]:
    ...


def script(  # noqa: PLR0913
    fn: typing.Callable[..., str] | None = None,
    *,
    name: str | None = None,
    extra_args: bool | None = False,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[TaskTypeOrProxy] | None = None,
    after: typing.Sequence[TaskTypeOrProxy] | None = None,
    cleanup: typing.Sequence[TaskTypeOrProxy] | None = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
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
    :param name: The name of the script.
    :param extra_args: If the script accepts extra arguments.
    :param bind: If true, the first parameter of the function will be the
        task class instance.
    :param condition: The condition to check before running the script.
    :param before: The tasks to run before the script.
    :param after: The tasks to run after the script.
    :param cleanup: The tasks to run after the script, even if it fails.
    :param env: The environment variables for the script.
    :param cwd: The working directory for the script.

    :returns: The task class, or, if `fn` is None, a partial function to be
        used as a decorator for a function.
    '''
    return generic_task_factory(
        fn,
        name=name,
        extra_args=extra_args,
        bind=bind,
        condition=condition,
        before=before,
        after=after,
        cleanup=cleanup,
        bases=(tasks.Script,),
        override_method=tasks.Script.get_script.__name__,
        extra_kwds={"env": env, "cwd": cwd},
    )


@typing.overload
def command(
    fn: typing.Callable[..., typing.Sequence[str]],
) -> type[tasks.Command]:
    ...


@typing.overload
def command(
    *,
    name: str | None = None,
    extra_args: bool | None = False,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[TaskTypeOrProxy] | None = None,
    after: typing.Sequence[TaskTypeOrProxy] | None = None,
    cleanup: typing.Sequence[TaskTypeOrProxy] | None = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
) -> PartialReturnType[tasks.Command]:
    ...


def command(  # noqa: PLR0913
    fn: typing.Callable[..., typing.Sequence[str]] | None = None,
    *,
    name: str | None = None,
    extra_args: bool | None = False,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[TaskTypeOrProxy] | None = None,
    after: typing.Sequence[TaskTypeOrProxy] | None = None,
    cleanup: typing.Sequence[TaskTypeOrProxy] | None = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
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
    :param name: The name of the command task.
    :param extra_args: If the command task accepts extra arguments.
    :param bind: If true, the first parameter of the function will be the
        task class instance.
    :param before: The tasks to run before the command task.
    :param after: The tasks to run after the command task.
    :param cleanup: The tasks to run after the command task, even if it fails.
    :param env: The environment variables for the command task.
    :param cwd: The working directory for the command task.

    :returns: The command task class, or, if `fn` is None, a partial function to be
        used as a decorator for a function.
    '''
    return generic_task_factory(
        fn,
        name=name,
        extra_args=extra_args,
        bind=bind,
        condition=condition,
        before=before,
        after=after,
        cleanup=cleanup,
        bases=(tasks.Command,),
        override_method=tasks.Command.get_cmd.__name__,
        extra_kwds={"env": env, "cwd": cwd},
    )


@typing.overload
def group(
    fn: typing.Callable,
) -> type[tasks.Group]:
    ...


@typing.overload
def group(  # noqa: PLR0913
    *,
    name: str | None = None,
    extra_args: bool | None = False,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[TaskTypeOrProxy] | None = None,
    after: typing.Sequence[TaskTypeOrProxy] | None = None,
    cleanup: typing.Sequence[TaskTypeOrProxy] | None = None,
) -> PartialReturnType[tasks.Group]:
    ...


def group(  # noqa: PLR0913
    fn: typing.Callable | None = None,
    *,
    name: str | None = None,
    extra_args: bool | None = False,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[TaskTypeOrProxy] | None = None,
    after: typing.Sequence[TaskTypeOrProxy] | None = None,
    cleanup: typing.Sequence[TaskTypeOrProxy] | None = None,
) -> DecoratorReturnType[tasks.Group]:
    """Create a group task from a function.

    The returned task will run in the same order without extra arguments.
    To add arguments to individual tasks in the group, you can use
    :func:`partial_task`.

    .. code-block:: python

        @group
        @arg("arg1")
        def my_group(arg1):
            return [task1, partial_task(task2, arg1)]

    :param fn: The function to create the group task from.
    :param name: The name of the group task.
    :param extra_args: If the group task accepts extra arguments.
    :param bind: If true, the first parameter of the function will be the
        task class instance.
    :param condition: The condition to check before running the group task.
    :param before: The tasks to run before the group task.
    :param after: The tasks to run after the group task.
    :param cleanup: The tasks to run after the group task, even if it fails.

    :returns: The group task class, or, if `fn` is None, a partial function to be
        used as a decorator for a function.
    """
    return generic_task_factory(
        fn,
        name=name,
        extra_args=extra_args,
        bind=bind,
        condition=condition,
        before=before,
        after=after,
        cleanup=cleanup,
        bases=(tasks.Group,),
        override_method=tasks.Group.get_tasks.__name__,
    )


@typing.overload
def thread_group(
    fn: typing.Callable,
) -> type[tasks.ThreadGroup]:
    ...


@typing.overload
def thread_group(
    *,
    name: str | None = None,
    extra_args: bool | None = False,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[TaskTypeOrProxy] | None = None,
    after: typing.Sequence[TaskTypeOrProxy] | None = None,
    cleanup: typing.Sequence[TaskTypeOrProxy] | None = None,
) -> PartialReturnType[tasks.ThreadGroup]:
    ...


def thread_group(  # noqa: PLR0913
    fn: typing.Callable | None = None,
    *,
    name: str | None = None,
    extra_args: bool | None = False,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[TaskTypeOrProxy] | None = None,
    after: typing.Sequence[TaskTypeOrProxy] | None = None,
    cleanup: typing.Sequence[TaskTypeOrProxy] | None = None,
) -> DecoratorReturnType[tasks.ThreadGroup]:
    """Create a thread group task from a function.

    The returned task will run in parallel. To add arguments to individual tasks
    in the group, you can return an instance of `partial_task` with the task and the
    arguments.

    Note that the tasks run in separate threads, so they should be thread-safe. This
    means that they are also affected by the Global Interpreter Lock (GIL).

    .. code-block:: python

        @thread_group
        @arg("arg1")
        def my_group(arg1):
            return [task1, partial_task(task2, arg1)]

    :param fn: The function to create the thread group task from.
    :param name: The name of the thread group task.
    :param extra_args: If the thread group task accepts extra arguments.
    :param bind: If true, the first parameter of the function will be the
        task class instance.
    :param condition: The condition to check before running the thread group task.
    :param before: The tasks to run before the thread group task.
    :param after: The tasks to run after the thread group task.
    :param cleanup: The tasks to run after the thread group task, even if it fails.

    :returns: The thread group task class, or, if `fn` is None, a partial function to
        be used as a decorator for a function.
    """
    return generic_task_factory(
        fn,
        name=name,
        extra_args=extra_args,
        bind=bind,
        condition=condition,
        before=before,
        after=after,
        cleanup=cleanup,
        bases=(tasks.ThreadGroup,),
        override_method=tasks.ThreadGroup.get_tasks.__name__,
    )
