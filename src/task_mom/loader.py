"""Task loader."""

from task_mom.namespace import Namespace, global_namespace
from task_mom.tasks import Task


def load_tasks_from_module(module):
    """Load tasks from a module."""
    modules = [(module, global_namespace)]
    while modules:
        module, namespace = modules.pop()
        if hasattr(module, "MOM_NAMESPACES"):
            for name, sub_module in module.MOM_NAMESPACES.items():
                sub_namespace = Namespace(name=name, parent=namespace)
                modules.append((sub_module, sub_namespace))
        for name, obj in module.__dict__.items():
            if isinstance(obj, type) and issubclass(obj, Task):
                aliases = getattr(obj, "alias", None)
                if isinstance(aliases, str):
                    aliases = [aliases]
                if aliases:
                    for alias in aliases:
                        namespace.register(obj, name=alias)
                else:
                    namespace.register(obj, name=name)
