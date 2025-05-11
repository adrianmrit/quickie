from quickie import tasks, Namespace, task
from quickie import app

from . import nested

namespace = Namespace()
namespace.add(nested, path="nested")


@task(name="hello")
class HelloWorld(tasks.Task):
    """Hello world task."""

    def run(self, **kwargs):
        app.console.print("Hello world!")
        app.console.print_info("This is an info message.")
        app.console.print_error("This is an error message.")
        app.console.print_warning("This is a warning message.")
        app.console.print_success("This is a success message.")


@task
def other_task():
    app.console.print("Other task.")


namespace.add(
    {"nested_again": nested, "": {"task": [HelloWorld, other_task]}}, path="dict"
)


class Holder:
    task = HelloWorld  # loaded
    other_attr = "other"  # not loaded
    nested = nested  # not loaded


namespace.add(Holder, path="cls_holder")  # technically allowed
