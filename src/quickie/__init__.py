#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""A CLI tool for quick tasks."""
from quickie.factories import arg, command, generic_task_factory, script, task
from quickie.tasks import Command, Group, Script, Task, ThreadGroup

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
    "task",
    "script",
    "command",
    "arg",
    "generic_task_factory",
]
