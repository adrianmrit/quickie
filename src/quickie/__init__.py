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
    Script,
    Task,
    ThreadGroup,
)
from quickie._namespace import Namespace
from quickie.config import app, console, logger
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
    "Task",
    "Script",
    "Command",
    "Group",
    "ThreadGroup",
    "Namespace",
    "task",
    "script",
    "command",
    "Arg",
    "task_factory_helper",
    "group",
    "thread_group",
]
