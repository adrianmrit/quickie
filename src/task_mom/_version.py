"""Read the version from installed package data."""
import importlib.metadata

__version__ = importlib.metadata.Distribution.from_name("task-mom").version
