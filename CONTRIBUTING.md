# Contributing to Quickie

Thanks for your interest in contributing! This guide covers how to set up the project, run the checks that are enforced in CI, and submit changes.

## Development setup

The project uses [uv](https://docs.astral.sh/uv/) for dependency management and requires **Python 3.12+**.

```bash
# Fork the repository on GitHub, then clone your fork:
git clone https://github.com/<your-username>/quickie.git
cd quickie

# Install dependencies
uv sync --dev

# Install the pre-commit hooks
uv run pre-commit install
```

## Commands

| Task | Command |
| ---- | ------- |
| Run the test suite | `uv run pytest` |
| Run tests with coverage | `uv run pytest --cov --cov-report=term-missing --cov-fail-under=95` |
| Lint | `uv run ruff check . --select F401,F811` |
| Format (write) | `uv run ruff format .` |
| Format (check) | `uv run ruff format --check .` |
| Pre-commit (all files) | `uv run pre-commit run --all-files` |

## Checks enforced in CI

GitHub Actions runs the following on every push and pull request (see `.github/workflows/ci.yml`):

1. **Tests** — `pytest` with coverage; the build fails if total coverage drops below **95%**.
2. **Linting** — `ruff check . --select F401,F811` (unused imports and redefinitions).
3. **Formatting** — `ruff format --check .`.
4. **Pre-commit** — `pre-commit run --all-files`.

## Coverage

New code should be covered by tests. `src/quickie/__main__.py` is a thin wrapper around `quickie._cli.main`; the relevant tests live in `tests/test_main.py`.

To see the coverage report:

```bash
uv run pytest --cov --cov-report=html
```

## Submitting changes

1. Fork the repository on GitHub.
2. Clone your fork and create a branch off `main`.
3. Make your changes, adding or updating tests as appropriate.
4. Run the checks listed above and make sure they pass.
5. Push your branch to your fork and open a pull request against the upstream `main` branch. CI will run the full suite automatically.

If CI fails, the `Checks` tab of the pull request will show which step (tests, lint, format, or pre-commit) needs attention.
