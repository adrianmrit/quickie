# Quickie Change Log

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
