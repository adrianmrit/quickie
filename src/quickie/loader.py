"""Task loader."""

from quickie.namespace import Namespace
from quickie.tasks import Task


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
            for obj in module.__dict__.values():
                if isinstance(obj, type) and issubclass(obj, Task):
                    meta = getattr(obj, "_meta")
                    if meta.private:
                        continue
                    aliases = meta.name
                    if isinstance(aliases, str):
                        aliases = [aliases]
                    for alias in aliases:
                        namespace.register(obj, name=alias)
