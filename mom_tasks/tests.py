from task_mom import tasks


class Test(tasks.ScriptTask):
    """Test task."""

    class Meta:
        alias = "test"
        allow_unknown_args = True

    def get_script(self, *args) -> str:
        args = " ".join(args)
        script = f"python -m pytest {args}"
        self.print(f"Running: {script}")
        return script


class Other(tasks.ScriptTask):
    """Other task."""

    class Meta:
        alias = "other"
        allow_unknown_args = True

    def get_script(self, *args) -> str:
        args = " ".join(args)
        script = f"echo {args}"
        self.print(f"Running: {script}")
        return script
