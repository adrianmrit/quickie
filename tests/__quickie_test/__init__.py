from quickie import tasks

from . import nested

QCK_NAMESPACES = {
    "nested": nested,
}


class HelloWorld(tasks.Task):
    """Hello world task."""

    class Meta:
        name = "hello"

    def run(self, **kwargs):
        self.print("Hello world!")
        self.print_info("This is an info message.")
        self.print_error("This is an error message.")
        self.print_warning("This is a warning message.")
        self.print_success("This is a success message.")
