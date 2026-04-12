# Quickie Change Log

## Unreleased

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

### Deprecated

- `qkg` command is now a backward-compatibility alias for `qk --global`. Existing users may continue using `qkg`, but `qk --global` is recommended.

### Fixed

- Can retrieve the file and line of tasks defined from functions wrapped with `functools.wraps`.
- `FilesModified` condition now takes a cache id explicitly.
- `Command` now falls back to `sys.executable` or `python3` when the `python` binary is not found in PATH.

### Migration Notes

- **For project users**: No changes required. Running `qk` from anywhere in your project will automatically use the project-specific version without manual venv activation.
- **For global task users**: Existing `qkg` aliases continue to work. Optionally migrate to `qk --global` for consistency.
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
