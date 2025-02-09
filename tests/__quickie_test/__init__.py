from quickie import tasks, Namespace, task
from quickie.utils.cli import console

from . import nested

namespace = Namespace()
namespace.add(nested, path="nested")


class HelloWorld(tasks.Task, name="hello"):
    """Hello world task."""

    def run(self, **kwargs):
        console.print("Hello world!")
        console.print_info("This is an info message.")
        console.print_error("This is an error message.")
        console.print_warning("This is a warning message.")
        console.print_success("This is a success message.")


@task
def other_task():
    console.print("Other task.")


namespace.add(
    {"nested_again": nested, "": {"task": [HelloWorld, other_task]}}, path="dict"
)


class Holder:
    task = HelloWorld  # loaded
    other_attr = "other"  # not loaded
    nested = nested  # not loaded


namespace.add(Holder, path="cls_holder")  # technically allowed
