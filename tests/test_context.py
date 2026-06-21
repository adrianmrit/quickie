from collections import ChainMap
import os
from pathlib import Path
from quickie import app
from quickie.context import Context, load_env_file, resolve_wd
from unittest.mock import PropertyMock


class TestResolveWd:
    def test_none_uses_context_wd(self):
        result = resolve_wd(None)
        assert result == os.path.abspath(app.context.wd)

    def test_dot_uses_tasks_path_parent(self, mocker):
        mocker.patch.object(
            type(app),
            "tasks_path",
            new_callable=PropertyMock,
            return_value=Path("/some/project/_qk"),
        )
        result = resolve_wd(".")
        assert result == os.path.abspath("/some/project")

    def test_dot_slash_resolves_relative_to_tasks_parent(self, mocker):
        mocker.patch.object(
            type(app),
            "tasks_path",
            new_callable=PropertyMock,
            return_value=Path("/some/project/_qk"),
        )
        result = resolve_wd("./sub/dir")
        assert result == os.path.abspath("/some/project/sub/dir")

    def test_relative_joined_with_context_wd(self):
        result = resolve_wd("sub/dir")
        assert result == os.path.abspath(os.path.join(app.context.wd, "sub/dir"))

    def test_absolute_used_as_is(self):
        result = resolve_wd("/absolute/path")
        assert result == os.path.abspath("/absolute/path")


class TestLoadEnvFile:
    def test_returns_dict_from_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=qux\n")
        result = load_env_file(env_file)
        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_caller_joins_base_dir(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\n")
        result = load_env_file(tmp_path / ".env")
        assert result == {"KEY": "value"}

    def test_ignores_unset_values(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("PRESENT=yes\nEMPTY=\n")
        result = load_env_file(env_file)
        # EMPTY has an empty string value — python-dotenv returns "" not None for empty
        assert "PRESENT" in result
        assert result["PRESENT"] == "yes"

    def test_absolute_path_works(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("A=1\n")
        result = load_env_file(env_file)
        assert result == {"A": "1"}


class TestContext:
    def test_copy(self):
        context = Context(
            wd="test",
            env={"MY_VAR": "value"},
            inherit_env=False,
        )
        context_copy = context.copy()
        assert context is not context_copy
        assert context.wd == context_copy.wd
        assert context.env == context_copy.env
        assert context.env is not context_copy.env
        assert isinstance(context.env, ChainMap)


class TestContextFromEnvFile:
    def test_loads_env_from_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("DB_URL=postgres://localhost/test\n")
        ctx = Context.from_env_file(env_file, wd=tmp_path, inherit_env=False)
        assert ctx.env["DB_URL"] == "postgres://localhost/test"

    def test_explicit_env_overrides_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=from_file\n")
        ctx = Context.from_env_file(
            env_file, wd=tmp_path, env={"KEY": "explicit"}, inherit_env=False
        )
        assert ctx.env["KEY"] == "explicit"

    def test_relative_path_resolved_via_base_dir(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("VAR=hello\n")
        ctx = Context.from_env_file(
            ".env", wd=tmp_path, base_dir=tmp_path, inherit_env=False
        )
        assert ctx.env["VAR"] == "hello"

    def test_wd_defaults_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("X=1\n")
        ctx = Context.from_env_file(env_file, inherit_env=False)
        assert ctx.wd == Path(tmp_path)

    def test_inherit_env_false_excludes_os_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOST_ONLY", "should_be_absent")
        env_file = tmp_path / ".env"
        env_file.write_text("FILE_VAR=present\n")
        ctx = Context.from_env_file(env_file, wd=tmp_path, inherit_env=False)
        assert "HOST_ONLY" not in ctx.env
        assert ctx.env["FILE_VAR"] == "present"

    def test_inherit_env_true_includes_os_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOST_ONLY", "yes")
        env_file = tmp_path / ".env"
        env_file.write_text("FILE_VAR=present\n")
        ctx = Context.from_env_file(env_file, wd=tmp_path, inherit_env=True)
        assert ctx.env["HOST_ONLY"] == "yes"
