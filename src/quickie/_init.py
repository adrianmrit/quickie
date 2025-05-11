from pathlib import Path

INIT_CONTENT = """from quickie import task

@task
def hello():
    print("Hello, World!")
"""


def init(dir: str | Path):
    target_dir = Path(f"{dir}/_qk")
    if target_dir.exists():
        print("Quickie project already initialized")
        return
    target_dir.mkdir()
    with open(target_dir / "__init__.py", "w") as f:
        f.write(INIT_CONTENT)
    print("Initialized Quickie project")
    print("Run `qk hello` to test it out")
    print("Run `qk --help` for more information")
