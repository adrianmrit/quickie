from quickie import tasks


class Other(tasks.Script):
    """Other task."""

    class Meta:
        name = "other"
        extra_args = True

    def get_script(self, *args) -> str:
        args = " ".join(args)
        script = f"echo {args}"
        self.print(f"Running: {script}")
        return script
