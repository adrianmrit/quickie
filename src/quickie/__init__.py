#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""A CLI tool for quick tasks."""

from quickie.factories import (
    arg,
    command,
    generic_task_factory,
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
    lazy_task,
    partial_task,
    suppressed_task,
)
from quickie.utils.cli import console
from quickie._namespace import Namespace

from ._meta import __author__, __copyright__, __email__, __home__, __version__

__all__ = [
    "__author__",
    "__copyright__",
    "__email__",
    "__home__",
    "__version__",
    "Task",
    "Script",
    "Command",
    "Group",
    "ThreadGroup",
    "Namespace",
    "task",
    "script",
    "command",
    "arg",
    "generic_task_factory",
    "group",
    "thread_group",
    "lazy_task",
    "partial_task",
    "suppressed_task",
    "console",
]
