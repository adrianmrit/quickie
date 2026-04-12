# Quickie Global

This package provides a global `qkg` command for accessing global quickie tasks from anywhere on your system. It is designed to complement per-project quickie installations.

## How It Works

With the **smart launcher** in quickie 0.6.0+, the unified `qk` command automatically discovers and delegates to project-specific quickie installations. The `qkg` command and `qk --global` flag provide explicit access to global tasks defined in `~/_qkg`.

## Resolution Order

When you run a quickie command:

1. **For `qk taskname`**: Automatically searches for project-local `_qk` (recursively up from cwd), then delegates to that project's quickie installation.
2. **For `qk --global taskname` or `qkg taskname`**: Explicitly uses global tasks from `~/_qkg` without project discovery.

## Installing

It is recommended to use `pipx` to install the global runner in an isolated environment:

```sh
pipx install quickie-runner-global
qkg --help
```

This also enables:

```sh
qk --global taskname  # Explicit global mode
```

If you have any issues with the `quickie` package missing when running `qkg`, you can inject it manually:

```sh
pipx inject quickie-runner-global quickie-runner
```

## Migration from Older Versions

If you were using `qkg` as your primary tool to automatically find project tasks, note that the new smart launcher in `qk` provides this behavior by default. To maintain compatibility:

- **Old behavior**: `qkg` automatically found and delegated to project tasks → **New**: Use `qk` instead (automatic project discovery)
- **Global tasks**: `qkg` for global → **New**: Use `qk --global` or keep using `qkg` (backward compatible)
