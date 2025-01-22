from quickie import tasks
from quickie.utils.cli import console

from . import nested

NAMESPACES = {
    "nested": nested,
}


class HelloWorld(tasks.Task, name="hello"):
    """Hello world task."""

    def run(self, **kwargs):
        console.print("Hello world!")
        console.print_info("This is an info message.")
        console.print_error("This is an error message.")
        console.print_warning("This is a warning message.")
        console.print_success("This is a success message.")
