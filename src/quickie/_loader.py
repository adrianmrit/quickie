"""Logic for loading tasks from modules."""

import types

from quickie._namespace import Namespace
from quickie.tasks import Task


def load_tasks_from_module(module, namespace):
    """Load tasks from a module.

    :param module: The module to load tasks from.
    :param namespace: The namespace to load the tasks into.
    """
    modules_to_load = [(module, namespace)]
    handled = set()
    while modules_to_load:
        module, namespace = modules_to_load.pop()
        # Because the last modules to pop take precedence over previous ones,
        # we add the modules in reverse order. This way the first module will
        # be added last, and pop first. This ensures a precedence order consistent
        # with how Python imports work.
        if not isinstance(module, types.ModuleType):
            modules_to_load.extend((module, namespace) for module in reversed(module))
            continue

        if hasattr(module, "NAMESPACES") and (module, namespace) not in handled:
            # Tasks loaded in the last modules might override earlier ones.
            # Therefore we load the namespaces
            modules_to_load.append(([module], namespace))
            handled.add((module, namespace))
            for name, value in module.NAMESPACES.items():
                if name:
                    sub_namespace = Namespace(name=name, parent=namespace)
                else:
                    sub_namespace = namespace
                modules_to_load.append((value, sub_namespace))
        else:
            for obj in module.__dict__.values():
                if isinstance(obj, type) and issubclass(obj, Task):
                    # Private tasks do not have __qck_names
                    for alias in obj.__qck_names:
                        namespace.register(obj, name=alias)
