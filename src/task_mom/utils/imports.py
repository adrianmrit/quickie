"""Utilities for importing modules from paths."""

import importlib.util
import sys
from pathlib import Path


class InternalImportError(ImportError):
    """An internal import error."""


def module_name_from_path(path: Path, *, root: Path) -> str:
    """Get the module name from a path.

    Example:
        >>> module_name_from_path(Path("src/task_mom/utils/imports.py"), Path("src"))
        "task_mom.utils.imports"

    Args:
        path: The path to the module.
        root: The root path of the module.
    """
    path = path.with_suffix("")

    try:
        relative = path.relative_to(root)
    except ValueError:
        # Check if path is relative
        if path.is_absolute():
            path_parts = path.parts[1:]
        else:
            path_parts = path.parts
    else:
        path_parts = relative.parts

    if len(path_parts) >= 2 and path_parts[-1] == "__init__":
        path_parts = path_parts[:-1]
    return ".".join(path_parts)


def import_from_path(path: Path, *, root: Path = Path.cwd()):
    """Import a module from a path.

    Args:
        path: The path to the module.
        root: The root path of the module.

    Returns:
        The imported module.
    """
    module_name = module_name_from_path(path, root=root)
    try:
        return sys.modules[module_name]
    except KeyError:
        pass

    spec = None
    if "." not in module_name:
        # If the module is in the root package, we can use the meta path finder
        for meta_importer in sys.meta_path:
            spec = meta_importer.find_spec(module_name, [str(root)])
            if spec is not None:
                break

    if spec is None:
        spec = importlib.util.spec_from_file_location(module_name, path.with_suffix(""))

    if spec is None:
        raise InternalImportError(f"Could not import {path!r}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore
    return module


def try_import(module_name: str):
    """Try to import a module.

    If the name starts with a dot, it will be relative to the calling module.

    Args:
        module_name: The name of the module to import.

    Returns:
        The imported module or None if it could not be imported.
    """
    if module_name.startswith("."):
        # Get the name of the file from which this function was called
        caller = sys._getframe(1)
        parent_module = caller.f_globals["__package__"]
        module_name = module_name[1:]
        # Further dot-prefixed names are relative to the caller file
        while module_name.startswith("."):
            parent_module = ".".join(parent_module.split(".")[:-1])
            module_name = module_name[1:]
        module_name = f"{parent_module}.{module_name}"

    # Module relative to a folder further up the tree
    if module_name.startswith("."):
        return None

    try:
        return sys.modules[module_name]
    except KeyError:
        pass

    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None
