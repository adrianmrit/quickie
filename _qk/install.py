from quickie import Arg, script


@script(
    args=[
        Arg("--editable", "-e", action="store_true", help="Install in editable mode."),
        Arg("--dev", action="store_true", help="Install development dependencies."),
    ],
    extra_args=True,
)
def install(editable=False, dev=False):
    """Install the package with optional editable and development dependencies."""
    editable = "-e" if editable else ""
    dev = "[dev]" if dev else ""
    return f"""
    uv pip install {editable} .{dev}
    rm -rf build
    rm -rf src/quickie.egg-info
    """
