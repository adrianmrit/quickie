from task_mom import tasks
from task_mom.utils.imports import try_import

from .tests import *  # noqa: F403

try_import(".private")


@tasks.register(name="hello")
class HelloWorld(tasks.Task):
    """Hello world task."""

    def run(self, **kwargs):
        print("Hello world!")
