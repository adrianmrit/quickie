from task_mom import tasks

tests_namespace = tasks.Namespace("tests")


@tasks.register
@tests_namespace.register
@tasks.allow_unknown_args
class Test(tasks.ScriptTask):
    """Test task."""

    def get_script(self, *args) -> str:
        args = " ".join(args)
        script = f"python -m pytest {args}"
        self.writeln(f"Running: {script}")
        return script
