# Quickie Change Log

## Unreleased

### Changed

- Paths prefixed with ``./`` (e.g. ``"./subdir"``) in task ``wd`` and
  ``PathCompleter`` now resolve relative to the tasks module parent directory
  (the project root), independently of the current working directory. This
  aligns ``./`` with the existing ``"."`` (bare dot) behaviour.

### Added

- `PathCompleter` now accepts an optional `wd` parameter to control the
  directory paths are resolved relative to, following the same rules as task
  working directories.
- Added `resolve_wd()` function in `quickie.context` that encapsulates the
  working directory resolution logic, shared by `_BaseSubprocessTask` and
  `PathCompleter`.

## Release 0.9.1

### Changed

- Upgraded dependencies

## Release 0.9.0

### Changed

- `qk-mcp`: replaced per-call `module` path resolution with a static project
  registry. Projects are now declared at server startup via `--project NAME:PATH`
  or `--config FILE`; they cannot be changed by clients at runtime.
- `qk-mcp`: `list_tasks` and `run_task` now accept a `project` parameter
  (alias or path) instead of `module`. `list_tasks` returns one entry per
  project with keys `project`, `project_root`, and `tasks`.
- `qk-mcp`: `list_tasks` returns tasks for **all** registered projects when
  `project` is omitted (previously returned only the default project).
- `qk-mcp`: removed `--module` / `-m` and `--global` / `-g` flags (still
  supported by the `qk` CLI). Use `--project` to register a project path.


## Release 0.8.1

### Fixed

- Fixed `qk-mcp` subprocess resolution to prefer project-local `qk` executable/venv when available.
- Ensure `run_task` forwards `--module`/`--global` flags and isolates subprocess config.
- Tests: fixed asyncio mocks and added tests for MCP venv resolution.


## Release 0.8.0

### Added

- Added `qk-mcp` MCP stdio server.


## Release 0.7.0

### Added

- Added `load_env_file(path)` helper that loads a `.env` file and returns a `dict[str, str]` (variables without a value are omitted; empty values are kept). Exported from the top-level `quickie` package.
- Added `Context.from_env_file(path, *, wd, base_dir, env, inherit_env)` classmethod to build a `Context` pre-populated from a `.env` file. Explicit `env` values take precedence over file-loaded values. Exported from the top-level `quickie` package.
- Command and script tasks (and their subclasses) now accept an `env_file` attribute and constructor/decorator argument. The `.env` file is loaded lazily at execution time; relative paths are resolved from the quickie tasks root. Explicit `env` values override keys loaded from the file.
- Command and script tasks now fail fast on unexpected non-zero subprocess exit codes.
- Command and script tasks now support `expected_exit_codes` to allow non-zero results explicitly or disable exit code validation.
- Command and script tasks now support `timeout` (seconds per attempt), `retries` (additional attempts on failure), and `retry_delay` (seconds between attempts). Timeouts raise `SubprocessTimeoutError` (exit code 124). Both exit-code and timeout errors trigger the retry loop; warnings are logged for each failed attempt and retry.
- Command and script tasks now expose an `output_mode` parameter (and class attribute) accepting `OutputMode.STREAM` (default), `OutputMode.CAPTURE`, or `OutputMode.TEE`. `CAPTURE` silences the terminal and populates `CompletedProcess.stdout`/`.stderr` as bytes. `TEE` streams to the terminal *and* captures. String literals `"stream"`, `"capture"`, `"tee"` are accepted and coerced automatically. `OutputMode` is exported from the top-level `quickie` package.
- Added `@namespace` decorator that converts a plain function into a `Namespace` instance at module level. The function must return a list or dict of tasks/modules; the function name is used as the path prefix by default. Supports `@namespace(path=..., separator=...)` for explicit configuration.
- `TaskNotFoundError` now suggests close matches when the task name is similar to a registered key.
- Naming a `@namespace`-decorated function `_` now registers its tasks at the root (no prefix), removing the need to write `@namespace(path="")` explicitly.
- `Namespace` now supports a `factory` parameter (a zero-argument callable returning a list or dict). The factory is executed **lazily** — only when the namespace's tasks are first needed. `@namespace`-decorated functions automatically use this mechanism, so imports inside the function body are deferred until the namespace is actually accessed.

### Changed

- `QuickieError` now declares `exit_code` as a class-level attribute (default `1`); subclasses override it declaratively. The `__init__` `exit_code` parameter is now optional and only used when a per-instance override is needed.
- `TaskNotFoundError` exit code changed from `1` to `127` (POSIX shell "command not found" convention).
- `TasksModuleNotFoundError` exit code changed from `2` to `78` (`EX_CONFIG` from sysexits.h — configuration/environment problem).
- `SubprocessTimeoutError` exit code `124` is now a class-level attribute (previously passed at instance construction).
- `Task.__call__`, `Task.full_run`, and `Task.run` now carry explicit return-type annotations (`Any`). `Command.run` and `Script.run` are annotated `subprocess.CompletedProcess[bytes]`.
- `Group.run` now returns `list[Any]` of sub-task results in definition order (previously returned `None`).
- `ThreadGroup.run` now returns `list[Any]` of sub-task results in **definition order**, not completion order (previously returned `None`).
- `ThreadGroup` now collects **all** sub-task exceptions and raises them together as an `ExceptionGroup` (previously only the first exception was surfaced; the rest were silently dropped). Use `except*` to handle individual exception types.
- `Namespace` now accepts a `separator` parameter (default `":"`); the separator is forwarded through all path-building helpers so sub-paths within a namespace use a consistent, per-instance separator.
- Circular-reference detection in namespace resolution now uses back-edge (DFS ancestry) tracking instead of global-visit tracking, correctly allowing the same object to appear under multiple namespace keys (shared references / DAGs) while still raising `CircularDependencyError` for genuine cycles.
- `RootNamespace.load()` is now **shallow**: `Task` objects found directly on the module are registered immediately, while `Namespace` objects are stored in a pending queue and resolved on demand.

### Fixed

- Documented direct task-to-task composition pattern: call a task instance from within another task's `run()` to receive its result.

## Release 0.6.0

### Added

- **Smart launcher for unified qk command**: The global `qk` command now automatically discovers project-local quickie installations and delegates to them, eliminating the need for manual venv activation. Each project can pin its own version while using the same `qk` command.
- `--global` flag to `qk` command to explicitly use global tasks from `~/_qkg` without project discovery.
- Project discovery algorithm that searches for `_qk` directory or `_qk.py` file starting from the current directory and traversing parent directories.
- Environment detection supporting uv-managed virtual environments, generic venv paths, and explicit path override via `QK_EXECUTABLE` environment variable.
- Recursion guard to prevent infinite delegation loops when project environment is misconfigured.
- Comprehensive error messages with attempted paths and setup guidance when project or executable cannot be found.

### Changed

- `qk` is now the primary entry point with smart launcher behavior. It first attempts to discover and delegate to a project-local quickie installation before falling back to the local CLI logic.
- `--global` flag is now the recommended way to access global tasks instead of requiring separate `qkg` command.
- Installation documentation updated to emphasize the automatic launcher flow as the recommended usage pattern.
- Default task names are transformed to lowercase, contiguous or single underscores are replaced with a single dash, and leading and trailing underscores/dashes are removed.

### Removed

- `quickie-runner-global` package and the `qkg` command have been removed. Use `qk --global` or `qk -g` instead.

### Fixed

- Can retrieve the file and line of tasks defined from functions wrapped with `functools.wraps`.
- `FilesModified` condition now takes a cache id explicitly.
- `Command` now falls back to `sys.executable` or `python3` when the `python` binary is not found in PATH.

### Migration Notes

- **For project users**: No changes required. Running `qk` from anywhere in your project will automatically use the project-specific version without manual venv activation.
- **For global task users**: Migrate from `qkg` to `qk --global` or `qk -g`. The `quickie-runner-global` package and `qkg` command are no longer available.
- **For users with multiple project versions**: Your setup is now natively supported. Each project can pin its own quickie version, and `qk` will automatically delegate to the correct version.

## Release 0.1.0

- Initial release.

## Release 0.2.0

### Added

- Create tasks from functions.
- Add arguments to the parser of tasks via decorators.
- Define tasks that must run before or after another task.
- Define cleanup tasks for a task.
- Allow conditions for running tasks.
- Define partial tasks.
- Load from another task by name.

### Changed

- Renamed classes and parameters for clarity.
- Removed support for file-based configuration in favor of environment variables.
- Removed `-g` argument in favor of separate global runner.

## Release 0.2.1

Fixes for global runner.

## Release 0.2.2

Fixes for global runner.

## Release 0.3.0

### Changed

- Removed Task.Meta and Task.DefaultMeta in favor of configuration in the task class.
- Task names inferred from class name preserve the case.
- Refactored and moved things around.
- Task classes starting with an underscore are now considered private by default.
- Namespace tasks using the `NAMESPACES` attribute instead of `QCK_NAMESPACES`.
- `NAMESPACES` (previously `QCK_NAMESPACES`) now also accepts a list of modules to load for
  a single namespace.

## Release 0.3.1

### Changed

- fix quickie-runner-global dependencies


## Release 0.3.2

### Added

- Listing tasks also shows the file and line where the task is defined.

### Fixed

- Fix bug causing tasks the help message for tasks to not include the docstring.


## Release 0.3.3

### Changed

- Tasks are listed sorted by location, and grouped by class, creating a new table for aliases.


## Release 0.4.0

### Changed

- NAMESPACES now accepts and ignores null values.
- Command now accepts unix style command strings.
- Script now allows defining the executable
- Cleaner exit on keyboard interrupt.
- Changed command from `qck` and `qckg` to `qk` and `qkg`.


## Release 0.5.0

### Removed
- Removed `partial_task`. `functools.partial` can be used instead.
- Removed `lazy_task`. `lambda: task()` can be used in most cases.
- Removed other proxy task types.

### Changed

- Replace NAMESPACES with Namespace class.
- Pretty printing and input can be done via a separate global console instance instead of through the task.
- Improved configuration.
- Parent process env variables are now passed to the child process even if some variables are overwritten.
- Changed the way command line arguments are defined in the task.
- Some task properties are now cached and evaluated when needed instead of at task initialization time, potentially
  improving performance in some cases.
- Using task instances instead of task classes for the task registry.
- Before, after and cleanup tasks can now be any callable, not just a task.
- Moved more task class attributes to initialization time, so that they can be overridden by the task instance.
- Changed project and user folders to `_qk` and `_qkg` respectively.

### Fixed
- Fix type hinting for task decorators.
- Fix bug causing the autocomplete to suggest files when calling `qk` with no arguments.

### Added

- Tasks can be skipped without stopping all pending tasks.
- Can skip logging for a task, to exclude sensitive information.
- Add logging and logging levels.
- Documentation for custom task factories.
- Can define the working directory for a command or script to be the parent of the tasks directory.


## Release 0.5.1

### Changed
- Only show error tracebacks when verbosity is set to 2 or higher.
