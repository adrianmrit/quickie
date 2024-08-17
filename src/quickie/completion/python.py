"""Python completers for quickie."""

import ast
import typing

from quickie.completion import PathCompleter


class PytestCompleter(PathCompleter):
    """For auto-completion of paths, but also adds python module completion.

    It auto-completes paths as usual, but if the path points to a python file,
    it will suggest to add `::`, and classes/functions after that.

    For example a suggestion can look like `path/to/file.py::MyClass::my_function`.
    """

    @typing.override
    def complete(self, prefix, **kwargs):
        path = prefix.split("::")
        path = [part for part in path if part]
        node_names = []
        partial_name = None

        if len(path) == 1:
            file_path = path[0]
        elif path:
            file_path = path[0]
            node_names = path[1:]
            if not prefix.endswith("::"):
                partial_name = node_names.pop()
        else:
            file_path = prefix

        if file_path.endswith(".py"):
            pre_resolved_path = file_path
            if node_names:
                pre_resolved_path += "::" + "::".join(node_names)

            return [
                f"{pre_resolved_path}::{node_name}"
                for node_name in self._get_python_paths(
                    file_path, node_names, partial_name
                )
            ]
        else:
            return super().complete(prefix=file_path, **kwargs)

    @typing.override
    def _get_paths(self, prefix: str) -> typing.Generator[str, None, None]:
        paths = super()._get_paths(prefix)
        for path in paths:
            yield path
            if path.endswith(".py"):
                yield f"{path}::"

    def _read_python_file(self, file_path: str) -> str:
        """Read the python file to a string."""
        with open(file_path) as file:
            return file.read()

    def _get_python_paths(
        self, file_path: str, python_path: list[str], partial_name: str | None
    ) -> typing.Generator[str, None, None]:
        """Complete the module."""
        try:
            tree = ast.parse(self._read_python_file(file_path), file_path)
        except SyntaxError:
            return

        # resolve the tree up to the last node
        for item in python_path:
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == item:
                    tree = node
                    break
            else:
                # Either no class with the name was found, or the node was not a class
                return

        # Return immediate children of the class or module
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if partial_name and not node.name.startswith(partial_name):
                    continue

                yield node.name
                # Because the class might contain inner tests
                if isinstance(node, (ast.ClassDef)):
                    yield node.name + "::"
