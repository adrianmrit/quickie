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
    """A finder specifically for a single module or package.

    This allows to import a module or package from a specific path without
    adding the path to sys.path or allowing to import other modules from the
    same path.
    """

    def __init__(self, module_path: str | Path):
        """Initialize the finder."""
        self.module_path = Path(module_path)
        self.module_name = self.module_path.stem
        self.is_package = (self.module_path / "__init__.py").exists()

    def find_spec(self, fullname, path=None, target=None):
        """Find the module spec."""
        if fullname != self.module_name:
            return None

        if self.is_package:
            return self._find_package_spec(fullname)
        else:
            return self._find_module_spec(fullname)

    def _find_module_spec(self, fullname):
        py_file = self.module_path.with_suffix(".py")
        if not py_file.exists():
            return None

        loader = SourceFileLoader(fullname, str(py_file))
        return machinery.ModuleSpec(fullname, loader, origin=str(py_file))

    def _find_package_spec(self, fullname):
        init_path = self.module_path / "__init__.py"
        if not init_path.exists():
            return None

        loader = SourceFileLoader(fullname, str(init_path))
        spec = machinery.ModuleSpec(
            fullname, loader, origin=str(init_path), is_package=True
        )
        spec.submodule_search_locations = [str(self.module_path)]
        return spec


def import_from_path(path):
    """Import a module from a path."""
    path = Path(path)
    module_name = path.stem

    if path.is_file() and path.suffix == ".py":
        parent_path = path.parent
    elif path.is_dir():
        parent_path = path
        module_name = path.name
    else:
        raise InternalImportError(f"Path {path} is not a valid module or package")

    finder = _Finder(path)

    # Add the Finder to the meta path
    sys.meta_path.append(finder)

    try:
        # Ensure parent path is in sys.path to resolve submodules
        sys.path.insert(0, str(parent_path))
        # Perform the import
        module = importlib.import_module(module_name)
        return module
    except ImportError as e:
        raise InternalImportError(f"Could not import {path}") from e
    finally:
        # Clean up by removing the Finder from the meta path and sys.path
        sys.meta_path.remove(finder)
        sys.path.remove(str(parent_path))
