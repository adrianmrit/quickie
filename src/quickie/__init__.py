#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""A CLI tool for quick tasks."""

from __future__ import annotations

import typing

from ._meta import __author__, __copyright__, __email__, __home__, __version__

if typing.TYPE_CHECKING:
    # Static imports for type checkers (Pylance/Pyright) — never executed at runtime
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
    from quickie import context
    from quickie.context import Context, load_env_file
    from quickie.utils.argparser import Arg

__all__ = [
    "__author__",
    "__copyright__",
    "__email__",
    "__home__",
    "__version__",
    "app",
    "console",
    "logger",
    "context",
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

# Lazy import mapping: symbol name -> (module_path, symbol_name)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # factories
    "command": ("quickie.factories", "command"),
    "task_factory_helper": ("quickie.factories", "task_factory_helper"),
    "group": ("quickie.factories", "group"),
    "script": ("quickie.factories", "script"),
    "task": ("quickie.factories", "task"),
    "thread_group": ("quickie.factories", "thread_group"),
    # tasks
    "Command": ("quickie.tasks", "Command"),
    "Group": ("quickie.tasks", "Group"),
    "OutputMode": ("quickie.tasks", "OutputMode"),
    "Script": ("quickie.tasks", "Script"),
    "Task": ("quickie.tasks", "Task"),
    "ThreadGroup": ("quickie.tasks", "ThreadGroup"),
    # namespace
    "Namespace": ("quickie._namespace", "Namespace"),
    "namespace": ("quickie._namespace", "namespace"),
    # config
    "app": ("quickie.config", "app"),
    "console": ("quickie.config", "console"),
    "logger": ("quickie.config", "logger"),
    # context
    "context": ("quickie", "context"),
    "Context": ("quickie.context", "Context"),
    "load_env_file": ("quickie.context", "load_env_file"),
    # utils
    "Arg": ("quickie.utils.argparser", "Arg"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, symbol_name = _LAZY_IMPORTS[name]
        import importlib

        module = importlib.import_module(module_path)
        value = getattr(module, symbol_name)
        # Cache on the module so subsequent accesses are fast
        globals()[name] = value
        return value
    raise AttributeError(f"module 'quickie' has no attribute {name!r}")
