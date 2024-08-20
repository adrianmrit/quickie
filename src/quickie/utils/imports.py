"""Utilities for importing modules."""

import importlib
import importlib.abc
import importlib.util
import sys
from importlib import machinery
from importlib.machinery import SourceFileLoader
from pathlib import Path


class InternalImportError(ImportError):
    """An internal import error."""


class _Finder(importlib.abc.MetaPathFinder):
    """A finder specifically for a single module or package."""

    def __init__(self, *, path: Path, module_name: str):
        """Initialize the finder."""
        self.path = path
        self.module_name = module_name

    def find_spec(self, fullname, path=None, target=None):
        """Find the module spec."""
        if fullname != self.module_name:
            return None

        loader = SourceFileLoader(fullname, str(self.path))
        spec = machinery.ModuleSpec(fullname, loader, origin=str(self.path))
        if self.path.name == "__init__.py":
            spec.submodule_search_locations = [str(self.path.parent)]
        return spec


def import_from_path(path):
    """Import a module from a path."""
    path = Path(path)

    if path.is_file():
        parent_path = path.parent
        module_name = path.stem
        module_file = path
    elif path.is_dir():
        parent_path = path
        module_name = path.name
        module_file = path / "__init__.py"
    else:
        raise InternalImportError(f"Path {path} is not a valid module or package")

    finder = _Finder(path=module_file, module_name=module_name)

    # Add the Finder to the meta path

    try:
        sys.meta_path.append(finder)
        # Ensure parent path is in sys.path to resolve submodules
        sys.path.insert(0, str(parent_path))
        # Perform the import
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise InternalImportError(f"Could not import {path}") from e
    else:
        # Fixes a bug where the __file__ is not set, thus some inspect functions fail
        module.__file__ = str(module_file)

        return module
    finally:
        # We only needed the finder and path temporarily
        # Remove them to avoid unwanted side effects
        sys.meta_path.remove(finder)
        sys.path.remove(str(parent_path))
