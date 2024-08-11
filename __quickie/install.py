from quickie import arg, command, script


@script
@arg("--editable", "-e", action="store_true", help="Install in editable mode.")
@arg("--dev", action="store_true", help="Install development dependencies.")
def local(editable=False, dev=False):
    editable = "-e" if editable else ""
    dev = "[dev]" if dev else ""
    return f"""
    pipx install {editable} .{dev} --force
    rm -rf build
    rm -rf src/quickie.egg-info
    """


@command
def dev():
    return ["pip", "install", ".[dev]"]
