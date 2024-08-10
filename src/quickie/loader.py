"""Task loader."""

from pathlib import Path

from quickie import constants
from quickie.errors import TasksModuleNotFoundError
from quickie.namespace import Namespace
from quickie.tasks import Task


def get_default_module_path():
    """Get the default module path."""
    current = Path.cwd()
    while True:
        path = current / constants.TASKS_PATH
        if (path).exists():
            return path
        if current == current.parent:
            break
        current = current.parent
    raise TasksModuleNotFoundError(constants.TASKS_PATH)


def load_tasks_from_module(module, namespace):
    """Load tasks from a module."""
    modules = [(module, namespace)]
    handled_modules = set()
    while modules:
        module, namespace = modules.pop()
        # If the module has a namespace, we handle them first. This way
        # if their namespace name is empty, and there is a task with the same
        # name in both the parent module and the child module, the parent
        # module task will be registered last and will be the one that is
        # returned when getting the task by name.
        if hasattr(module, "QCK_NAMESPACES") and module not in handled_modules:
            modules.append((module, namespace))
            handled_modules.add(module)
            for name, sub_module in module.QCK_NAMESPACES.items():
                if name:
                    sub_namespace = Namespace(name=name, parent=namespace)
                else:
                    sub_namespace = namespace
                modules.append((sub_module, sub_namespace))
        else:
            for name, obj in module.__dict__.items():
                if isinstance(obj, type) and issubclass(obj, Task):
                    meta = getattr(obj, "_meta")
                    if meta.abstract:
                        continue
                    aliases = meta.alias
                    if isinstance(aliases, str):
                        aliases = [aliases]
                    for alias in aliases:
                        namespace.register(obj, name=alias)
