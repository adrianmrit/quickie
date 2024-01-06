"""Base classes for tasks.

Tasks are the main building blocks of task-mom. They are like self-contained
programs that can be run from the command line. They can be used to run
commands, or to run other tasks. They can also be used to group other tasks
together.
"""
import abc
import argparse
import typing

import classoptions


class TaskMetaclasss(classoptions.ClassOptionsMetaclass, abc.ABCMeta):
    """Metaclass for all tasks."""

    def __new__(mcs, name, bases, attrs):
        """Sets a default name for the task if not provided."""
        cls: Task = super().__new__(mcs, name, bases, attrs)  # type: ignore

        if getattr(cls._meta, "name", None) is None:
            cls._meta.name = cls.__name__.lower()

        return cls


class Task(metaclass=TaskMetaclasss):
    """Base class for all tasks."""

    class DefaultMeta:
        """Default metadata for tasks.

        These options are automatically inherited by subclasses.
        """

        name: str
        """The name of the task. Defaults to the name of the class in lowercase."""

        abstract = False
        """Whether the task is abstract. That is, it cannot be executed directly."""

    class Meta:
        """Metadata specific to the task where it is declared.

        These options are not inherited by subclasses.
        """

        abstract = True

    _meta: DefaultMeta
    """Metadata for the task."""

    def __init__(self):
        """Initialize the task."""
        self.parser = self.get_parser()
        self.add_arguments(self.parser)

    def get_parser(self) -> argparse.ArgumentParser:
        """Get the parser for the task."""
        parser = argparse.ArgumentParser(
            prog=self._meta.name, description=self.__doc__, add_help=False
        )
        return parser

    def add_arguments(self, parser: argparse.ArgumentParser):
        """Add arguments to the parser.

        This method should be overridden by subclasses to add arguments to the parser.

        Args:
            parser: The parser to add arguments to.
        """
        pass

    def get_help(self) -> str:
        """Get the help message of the task."""
        return self.parser.format_help()

    def run(self, **kwargs):
        """Run the task."""
        raise NotImplementedError

    def __call__(self, args: typing.Sequence[str]):
        """Call the task."""
        parsed_args = self.parser.parse_args(args)
        return self.run(**vars(parsed_args))


class ProgramTask(Task):
    """Base class for tasks that run a program."""

    class Meta:
        abstract = True

    program: str | None = None
    """The program to run."""

    program_args: typing.Sequence[str] | None = None
    """The program arguments. Defaults to the task arguments."""

    def get_program(self, **kwargs) -> str:
        """Get the program to run."""
        if self.program is None:
            raise NotImplementedError("Either set program or override get_program()")
        return self.program

    def get_program_args(self, **kwargs) -> typing.Sequence[str]:
        """Get the program arguments. Defaults to the task arguments."""
        return self.program_args or []

    @typing.override
    def run(self, **kwargs):
        """Run the task."""
        program = self.get_program(**kwargs)
        program_args = self.get_program_args(**kwargs)
        return self.run_program(program, program_args)

    def run_program(self, program: str, args: typing.Sequence[str]):
        """Run the program."""
        import subprocess

        result = subprocess.run([program, *args], check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Program failed with exit code {result.returncode}")
        return result


class ScriptTask(Task):
    """Base class for tasks that run a script."""

    class Meta:
        abstract = True

    script: str | None = None

    def get_script(self, **kwargs) -> str:
        """Get the script to run."""
        if self.script is None:
            raise NotImplementedError("Either set script or override get_script()")
        return self.script

    @typing.override
    def run(self, **kwargs):
        """Run the task."""
        script = self.get_script(**kwargs)
        self.run_script(script)

    def run_script(self, script: str):
        """Run the script."""
        import subprocess

        result = subprocess.run(script, shell=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Script failed with exit code {result.returncode}")
        return result
