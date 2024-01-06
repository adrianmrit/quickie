from task_mom import tasks

from .tests import *  # noqa: F403

try:
    from .private import *  # type: ignore # noqa: F403
except ImportError:
    pass


@tasks.register(name="hello")
class HelloWorld(tasks.Task):
    """Hello world task."""

    def run(self, **kwargs):
        print("Hello world!")
