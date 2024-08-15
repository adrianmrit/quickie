'''Factories for creating tasks from functions.

We can create tasks from functions using the `task`, `script`, and `command`
decorators. Additionally, we can add arguments to the tasks using the `arg`
decorator.

Examples:
```python
@task(name="hello", help="Hello world task.", bind=True)
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


class _OptionKwargs(typing.TypedDict):
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


def arg(
    *name_or_flags: str,
    completer: typing.Callable | None = None,
    **kwargs: typing.Unpack[_OptionKwargs],
):
    """Used to add arguments to the arguments parser of a task.

    Arguments are the same as the `add_argument` method of `ArgumentParser`, except
    for the `completer` argument which is a function that provides completion for
    the argument.

    Args:
        name_or_flags: The name or flags for the argument.
        completer: A function to provide completion for the argument.
        kwargs: The keyword arguments for the argument. See `add_argument` method
            of `ArgumentParser` for more information.
    """

    def decorator(fn):
        if isinstance(fn, tasks.TaskMeta):
            # decorator appears on top of a task decorator, or directly on top of a cls
            original_add_args = fn.add_args

            def add_args(self, parser: ArgumentParser):
                original_add_args(self, parser)
                parser.add_argument(*name_or_flags, **kwargs).completer = completer

            fn.add_args = add_args
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
            parser.add_argument(*name_or_flags, **kwargs).completer = completer

    return add_args


def generic_task_factory(  # noqa: PLR0913
    fn: typing.Callable | None = None,
    *,
    name: str | None = None,
    extra_args: bool = False,
    private: bool = False,
    help: str | None = None,
    short_help: str | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[tasks.Task] = None,
    after: typing.Sequence[tasks.Task] = None,
    cleanup: typing.Sequence[tasks.Task] = None,
    bases: tuple[type[tasks.Task], ...],
    override_method: str,
    extra_kwds: dict[str, typing.Any] | None = None,
    extra_meta_kwds: dict[str, typing.Any] | None = None,
):
    '''Create a task class from a function.

    You might find this useful when you have a base class for tasks and you want to
    create your own decorator that creates tasks from functions.

    Other decorators like `script` and `command` are implemented using this function.

    Example:
    ```python
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
    ```


    Args:
        fn: The function to create the task from. If None, a partial
            function will be returned, so you can use this function as a decorator
            with the arguments.
        name: The name of the task.
        extra_args: If the task accepts extra arguments.
        private: If the task is private.
        help: The help text for the task.
        short_help: The short help text for the task.
        bind: If true, the first parameter of the function will be the
            task class instance.
        condition: The condition to check before running the task.
        before: The tasks to run before the task.
        after: The tasks to run after the task.
        cleanup: The tasks to run after the task, even if it fails.
        bases: The base classes for the task.
        override_method: The method to override in the task.
        extra_kwds: Extra keyword arguments for the task class.
        extra_meta_kwds: Extra keyword arguments for the meta class.
    '''
    if fn is None:
        return functools.partial(
            generic_task_factory,
            name=name,
            extra_args=extra_args,
            private=private,
            help=help,
            short_help=short_help,
            bind=bind,
            condition=condition,
            before=before,
            after=after,
            cleanup=cleanup,
            bases=bases,
            override_method=override_method,
            extra_kwds=extra_kwds,
            extra_meta_kwds=extra_meta_kwds,
        )

    name = name or fn.__name__
    meta_cls = type(
        "Meta",
        (),
        {
            "name": name,
            "extra_args": extra_args,
            "private": private,
            "help": help,
            "short_help": short_help,
            **(extra_meta_kwds or {}),
        },
    )

    kwds = {"Meta": meta_cls}
    if extra_kwds is not None:
        kwds.update(extra_kwds)

    add_args = _get_add_args_method(fn)
    if add_args is not None:
        kwds["add_args"] = add_args

    if condition:
        kwds["condition"] = condition

    if before:
        kwds["before"] = before

    if after:
        kwds["after"] = after

    if cleanup:
        kwds["cleanup"] = cleanup

    if bind:
        new_fn = functools.partialmethod(fn)
    else:
        # Still wrap as a method
        def new_fn(_, *args, **kwargs):
            return fn(*args, **kwargs)

    kwds[override_method] = new_fn

    return type(name, bases, kwds)


def task(  # noqa: PLR0913
    fn: typing.Callable | None = None,
    *,
    name: str | None = None,
    extra_args: bool = False,
    private: bool = False,
    help: str | None = None,
    short_help: str | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[tasks.Task] = None,
    after: typing.Sequence[tasks.Task] = None,
    cleanup: typing.Sequence[tasks.Task] = None,
):
    '''Create a task from a function.

    Example:
    ```python
    @task(name="hello", help="Hello world task.", bind=True)
    def hello_task(task):
        task.console.print("Hello, task!")

    @task
    def hello_world():
        """Docstring will be used as help text."""
        print("Hello, world!")
    ```

    Args:
        fn (Callable): The function to create the task from.
        name: The name of the task.
        extra_args: If the task accepts extra arguments.
        private: If the task is private.
        help: The help text for the task.
        short_help: The short help text for the task.
        bind: If true, the first parameter of the function will be the
            task class instance.
        condition: The condition to check before running the task.
        before: The tasks to run before the task.
        after: The tasks to run after the task.
        cleanup: The tasks to run after the task, even if it fails.
    '''
    return generic_task_factory(
        fn,
        name=name,
        extra_args=extra_args,
        private=private,
        help=help,
        short_help=short_help,
        bind=bind,
        condition=condition,
        before=before,
        after=after,
        cleanup=cleanup,
        bases=(tasks.Task,),
        override_method=tasks.Task.run.__name__,
    )


def script(  # noqa: PLR0913
    fn: typing.Callable[..., str] | None = None,
    *,
    name: str | None = None,
    extra_args: bool = False,
    private: bool = False,
    help: str | None = None,
    short_help: str | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[tasks.Task] = None,
    after: typing.Sequence[tasks.Task] = None,
    cleanup: typing.Sequence[tasks.Task] = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
):
    '''Create a script from a function.

    Example:
    ```python
    @script(name="hello", help="Hello world script.", bind=True)
    def hello_script(task):
        return "echo Hello, script!"

    @script
    def hello_world():
        """Docstring will be used as help text."""
        return "echo Hello, world!"
    ```

    Args:
        fn (Callable): The function to create the script from.
        name: The name of the script.
        extra_args: If the script accepts extra arguments.
        private: If the script is private.
        help: The help text for the script.
        short_help: The short help text for the script.
        bind: If true, the first parameter of the function will be the
            task class instance.
        condition: The condition to check before running the script.
        before: The tasks to run before the script.
        after: The tasks to run after the script.
        cleanup: The tasks to run after the script, even if it fails.
        env: The environment variables for the script.
        cwd: The working directory for the script.
    '''
    return generic_task_factory(
        fn,
        name=name,
        extra_args=extra_args,
        private=private,
        help=help,
        short_help=short_help,
        bind=bind,
        condition=condition,
        before=before,
        after=after,
        cleanup=cleanup,
        bases=(tasks.Script,),
        override_method=tasks.Script.get_script.__name__,
        extra_kwds={"env": env, "cwd": cwd},
    )


def command(  # noqa: PLR0913
    fn: typing.Callable[..., typing.Sequence[str]] | None = None,
    *,
    name: str | None = None,
    extra_args: bool = False,
    private: bool = False,
    help: str | None = None,
    short_help: str | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[tasks.Task] = None,
    after: typing.Sequence[tasks.Task] = None,
    cleanup: typing.Sequence[tasks.Task] = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
):
    '''Create a command task from a function.

    Example:
    ```python
    @command(name="hello", help="Hello world command.", bind=True)
    def run_program(task):
        return ["program", "arg1", "arg2"]

    @command
    def hello_world():
        """Docstring will be used as help text."""
        return ["program", "arg1", "arg2"]
    ```

    Args:
        fn: The function to create the command task from.
        name: The name of the command task.
        extra_args: If the command task accepts extra arguments.
        private: If the command task is private.
        help: The help text for the command task.
        short_help: The short help text for the command task.
        bind: If true, the first parameter of the function will be the
            task class instance.
        before: The tasks to run before the command task.
        after: The tasks to run after the command task.
        cleanup: The tasks to run after the command task, even if it fails.
        env: The environment variables for the command task.
        cwd: The working directory for the command task.
    '''
    return generic_task_factory(
        fn,
        name=name,
        extra_args=extra_args,
        private=private,
        help=help,
        short_help=short_help,
        bind=bind,
        condition=condition,
        before=before,
        after=after,
        cleanup=cleanup,
        bases=(tasks.Command,),
        override_method=tasks.Command.get_cmd.__name__,
        extra_kwds={"env": env, "cwd": cwd},
    )


def group(  # noqa: PLR0913
    fn: typing.Callable | None = None,
    *,
    name: str | None = None,
    extra_args: bool = False,
    private: bool = False,
    help: str | None = None,
    short_help: str | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[tasks.Task] = None,
    after: typing.Sequence[tasks.Task] = None,
    cleanup: typing.Sequence[tasks.Task] = None,
):
    """Create a group task from a function.

    The returned task will run in the same order. To add arguments to individual
    tasks in the group, you can return an instance of `partial_task` with the task
    and the arguments.

    Example:
    ```python
    @group
    @arg("arg1")
    def my_group(arg1):
        return [task1, partial_task(task2, arg1)]
    ```

    Args:
        fn: The function to create the group task from.
        name: The name of the group task.
        extra_args: If the group task accepts extra arguments.
        private: If the group task is private.
        help: The help text for the group task.
        short_help: The short help text for the group task.
        bind: If true, the first parameter of the function will be the
            task class instance.
        condition: The condition to check before running the group task.
        before: The tasks to run before the group task.
        after: The tasks to run after the group task.
        cleanup: The tasks to run after the group task, even if it fails.
    """
    return generic_task_factory(
        fn,
        name=name,
        extra_args=extra_args,
        private=private,
        help=help,
        short_help=short_help,
        bind=bind,
        condition=condition,
        before=before,
        after=after,
        cleanup=cleanup,
        bases=(tasks.Group,),
        override_method=tasks.Group.get_tasks.__name__,
    )


def thread_group(  # noqa: PLR0913
    fn: typing.Callable | None = None,
    *,
    name: str | None = None,
    extra_args: bool = False,
    private: bool = False,
    help: str | None = None,
    short_help: str | None = None,
    bind: bool = False,
    condition: tasks.BaseCondition | None = None,
    before: typing.Sequence[tasks.Task] = None,
    after: typing.Sequence[tasks.Task] = None,
    cleanup: typing.Sequence[tasks.Task] = None,
):
    """Create a thread group task from a function.

    The returned task will run in parallel. To add arguments to individual tasks
    in the group, you can return an instance of `partial_task` with the task and the
    arguments.

    Note that the tasks run in separate threads, so they should be thread-safe. This
    means that they are also affected by the Global Interpreter Lock (GIL).

    Example:
    ```python
    @thread_group
    @arg("arg1")
    def my_group(arg1):
        return [task1, partial_task(task2, arg1)]
    ```

    Args:
        fn: The function to create the thread group task from.
        name: The name of the thread group task.
        extra_args: If the thread group task accepts extra arguments.
        private: If the thread group task is private.
        help: The help text for the thread group task.
        short_help: The short help text for the thread group task.
        bind: If true, the first parameter of the function will be the
            task class instance.
        condition: The condition to check before running the thread group task.
        before: The tasks to run before the thread group task.
        after: The tasks to run after the thread group task.
        cleanup: The tasks to run after the thread group task, even if it fails.
    """
    return generic_task_factory(
        fn,
        name=name,
        extra_args=extra_args,
        private=private,
        help=help,
        short_help=short_help,
        bind=bind,
        condition=condition,
        before=before,
        after=after,
        cleanup=cleanup,
        bases=(tasks.ThreadGroup,),
        override_method=tasks.ThreadGroup.get_tasks.__name__,
    )
