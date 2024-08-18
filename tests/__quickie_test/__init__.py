from quickie import tasks

from . import nested

NAMESPACES = {
    "nested": nested,
}


class HelloWorld(tasks.Task, name="hello"):
    """Hello world task."""

    def run(self, **kwargs):
        self.print("Hello world!")
        self.print_info("This is an info message.")
        self.print_error("This is an error message.")
        self.print_warning("This is a warning message.")
        self.print_success("This is a success message.")
