#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""A CLI tool for quick tasks."""

from quickie.factories import (
    command,
    task_factory_helper,
    group,
    script,
    task,
    thread_group,
)
from quickie.tasks import (
    Command,
    Group,
    OutputMode,
    Script,
    Task,
    ThreadGroup,
)
from quickie._namespace import Namespace, namespace
from quickie.config import app, console, logger
from quickie.context import Context, load_env_file
from quickie.utils.argparser import Arg

from ._meta import __author__, __copyright__, __email__, __home__, __version__

__all__ = [
    "__author__",
    "__copyright__",
    "__email__",
    "__home__",
    "__version__",
    "app",
    "console",
    "logger",
    "Context",
    "load_env_file",
    "Task",
    "Script",
    "Command",
    "Group",
    "ThreadGroup",
    "OutputMode",
    "Namespace",
    "namespace",
    "task",
    "script",
    "command",
    "Arg",
    "task_factory_helper",
    "group",
    "thread_group",
]
