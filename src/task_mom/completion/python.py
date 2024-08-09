"""Python completers for task_mom."""

import ast
import typing

from task_mom.completion.base import PathCompleter


class PytestCompleter(PathCompleter):
    """For auto-completing pytest arguments."""

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
            file_path = ""

        if file_path.endswith(".py"):
            pre_resolved_path = file_path
            if node_names:
                pre_resolved_path += "::" + "::".join(node_names)

            return [
                f"{pre_resolved_path}::{node_name}"
                for node_name in self.get_python_paths(
                    file_path, node_names, partial_name
                )
            ]
        else:
            paths = []
            for path in self.get_paths(prefix):
                paths.append(path)
                if path.endswith(".py"):
                    paths.append(f"{path}::")
            return paths

    def get_python_paths(
        self, file_path: str, python_path: list[str], partial_name: str | None
    ) -> typing.Generator[str, None, None]:
        """Complete the module."""
        with open(file_path) as file:
            tree = ast.parse(file.read(), file_path)

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
