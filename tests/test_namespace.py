"""Tests for the namespace system improvements."""

import types

import pytest

from quickie._namespace import (
    Namespace,
    RootNamespace,
    namespace,
    _merge_alias,
    _merge_aliases,
)
from quickie.errors import CircularDependencyError, TaskNotFoundError
from quickie.factories import task


def _mod(**kwargs):
    """Return a module stub whose __dict__ contains the given names."""
    mod = types.ModuleType("test_module")
    mod.__dict__.update(kwargs)
    return mod


# ---------------------------------------------------------------------------
# Phase 1 — separator wired through path-building helpers
# ---------------------------------------------------------------------------


class TestMergeAlias:
    def test_default_separator(self):
        assert _merge_alias("a", "b") == "a:b"

    def test_custom_separator(self):
        assert _merge_alias("a", "b", ".") == "a.b"

    def test_empty_root(self):
        assert _merge_alias("", "b", ".") == "b"

    def test_empty_alias(self):
        assert _merge_alias("a", "", ".") == "a"


class TestMergeAliases:
    def test_default_separator(self):
        assert _merge_aliases("ns", ["foo", "bar"]) == ["ns:foo", "ns:bar"]

    def test_custom_separator(self):
        assert _merge_aliases("ns", ["foo", "bar"], ".") == ["ns.foo", "ns.bar"]

    def test_empty_alias_in_list(self):
        # Empty string alias → registered at the root of this namespace (no separator)
        assert _merge_aliases("ns", ["foo", ""], ".") == ["ns.foo", "ns"]


class TestNamespaceSeparatorWired:
    def test_custom_separator_used_in_paths(self):
        @task
        def my_task():
            pass

        ns = Namespace({"sub": [my_task]}, path="root", separator=".")
        keys = dict(ns.items())
        assert "root.sub" in keys

    def test_nested_separator_respected(self):
        @task
        def my_task():
            pass

        ns = Namespace(separator="|")
        ns.add([my_task], "level")
        keys = dict(ns.items())
        assert "|level" not in keys  # path is "", so just "level"
        assert "level" in keys

    def test_separator_in_root_namespace_load(self):
        @task(name="t")
        def my_task():
            pass

        ns = Namespace({"sub": [my_task]}, path="root", separator=".")
        rns = RootNamespace()
        rns.load(_mod(ns=ns))
        # Namespace path "root.sub" is built with "."; task name joins with ":".
        assert any(k.startswith("root.sub") for k in rns)

    def test_nested_namespace_keeps_parent_path(self):
        @task(name="t")
        def t():
            pass

        inner = Namespace({"": [t]})
        outer = _mod(inner=inner)
        rns = RootNamespace()
        rns.load(_mod(ns=Namespace({"test": [outer]})))

        assert "test:t" in rns


# ---------------------------------------------------------------------------
# Phase 2 — circular reference detection (back-edge, not shared-ref)
# ---------------------------------------------------------------------------


class TestCircularReferenceDetection:
    def test_shared_reference_allowed(self):
        """The same module/object under two different keys must not raise."""

        @task(name="build")
        def build_task():
            pass

        shared = [build_task]
        ns = Namespace({"a": shared, "b": shared})
        rns = RootNamespace()
        # Must not raise — shared Namespace appears under two sibling keys
        rns.load(_mod(ns=ns))
        assert "a:build" in rns
        assert "b:build" in rns

    def test_namespace_shared_reference_allowed(self):
        """The same Namespace object under two sibling keys must not raise."""

        @task(name="t")
        def t():
            pass

        inner = Namespace({"": [t]}, path="inner")
        outer = Namespace({"x": inner, "y": inner})
        rns = RootNamespace()
        rns.load(_mod(outer=outer))
        # Tasks appear under both "a" and "b" paths
        assert any(k.endswith(":t") for k in rns)

    def test_direct_cycle_in_list_raises(self):
        """A list that contains itself must raise CircularDependencyError on access."""

        @task(name="looping")
        def looping_task():
            pass

        cycle: list = [looping_task]
        cycle.append(cycle)  # type: ignore[arg-type]
        ns = Namespace({"loop": cycle})
        rns = RootNamespace()
        rns.load(_mod(ns=ns))
        # Cycle is detected when the namespace is first resolved (lazy)
        with pytest.raises(CircularDependencyError, match="Circular reference"):
            list(rns)  # triggers _resolve_all

    def test_namespace_self_reference_raises(self):
        """A Namespace containing itself in _mappings raises CircularDependencyError on access."""
        ns: Namespace = Namespace()

        @task(name="self-ref")
        def self_ref():
            pass

        ns.add([self_ref], "items")
        # Manually inject self-reference into the internal mapping
        ns._mappings["items"].append(ns)  # type: ignore[attr-defined]
        rns = RootNamespace()
        rns.load(_mod(ns=ns))
        # Cycle is detected when the namespace is first resolved (lazy)
        with pytest.raises(CircularDependencyError, match="Circular reference"):
            list(rns)  # triggers _resolve_all


# ---------------------------------------------------------------------------
# Phase 3 — @namespace decorator
# ---------------------------------------------------------------------------


class TestNamespaceDecorator:
    def test_bare_form_returns_namespace_instance(self):
        @task(name="t")
        def t():
            pass

        @namespace
        def my_ns():
            return [t]

        assert isinstance(my_ns, Namespace)

    def test_bare_form_uses_function_name_as_path(self):
        @task(name="t")
        def t():
            pass

        @namespace
        def tools():
            return [t]

        rns = RootNamespace()
        rns.load(_mod(tools=tools))
        assert "tools:t" in rns

    def test_parametrised_form_explicit_path(self):
        @task(name="t")
        def t():
            pass

        @namespace(path="ci")
        def ci_tasks():
            return [t]

        rns = RootNamespace()
        rns.load(_mod(ci_tasks=ci_tasks))
        assert "ci:t" in rns

    def test_empty_path_registers_at_root(self):
        @task(name="root-task")
        def root_t():
            pass

        @namespace(path="")
        def root_extras():
            return [root_t]

        rns = RootNamespace()
        rns.load(_mod(root_extras=root_extras))
        assert "root-task" in rns

    def test_dict_return_supported(self):
        @task(name="migrate")
        def migrate():
            pass

        @task(name="seed")
        def seed():
            pass

        @namespace(path="db")
        def db_tasks():
            return {"": [migrate], "dev": [seed]}

        rns = RootNamespace()
        rns.load(_mod(db_tasks=db_tasks))
        assert "db:migrate" in rns
        assert "db:dev:seed" in rns

    def test_custom_separator(self):
        @task(name="t")
        def t():
            pass

        @namespace(path="root", separator=".")
        def tools():
            return {"sub": [t]}

        rns = RootNamespace()
        rns.load(_mod(tools=tools))
        # path built as "root.sub", task joined with DEFAULT_SEPARATOR
        assert any("root.sub" in k for k in rns)

    def test_discoverable_as_module_global(self):
        """load() must pick up a @namespace result sitting in a module-level dict."""

        @task(name="discovered")
        def discovered():
            pass

        @namespace
        def my_namespace():
            return [discovered]

        # Simulate a minimal module-like object
        mod = types.ModuleType("fake_module")
        mod.__dict__["my_namespace"] = my_namespace

        rns = RootNamespace()
        rns.load(mod)
        assert "my_namespace:discovered" in rns


# ---------------------------------------------------------------------------
# Phase 4 — "did you mean?" hint in TaskNotFoundError
# ---------------------------------------------------------------------------


class TestDidYouMean:
    def test_close_match_included_in_message(self):
        rns = RootNamespace()

        @task(name="build")
        def build():
            pass

        rns.register(build, namespace="build")
        with pytest.raises(TaskNotFoundError) as exc_info:
            _ = rns["biuld"]
        assert "Did you mean" in str(exc_info.value)
        assert "'build'" in str(exc_info.value)

    def test_no_close_match_no_suggestion(self):
        rns = RootNamespace()

        @task(name="build")
        def build():
            pass

        rns.register(build, namespace="build")
        with pytest.raises(TaskNotFoundError) as exc_info:
            _ = rns["zzzzzzzzz"]
        assert "Did you mean" not in str(exc_info.value)

    def test_multiple_close_matches(self):
        rns = RootNamespace()

        @task(name="test-unit")
        def test_unit():
            pass

        @task(name="test-integration")
        def test_integration():
            pass

        rns.register(test_unit, namespace="test-unit")
        rns.register(test_integration, namespace="test-integration")
        with pytest.raises(TaskNotFoundError) as exc_info:
            _ = rns["test-integratio"]
        msg = str(exc_info.value)
        assert "Did you mean" in msg
        assert "test-integration" in msg

    def test_no_candidates_no_suggestion(self):
        """When TaskNotFoundError is constructed without candidates, no hint."""
        err = TaskNotFoundError("missing")
        assert "Did you mean" not in str(err)

    def test_exit_code_preserved(self):
        err = TaskNotFoundError("x", candidates=["x-other"])
        assert err.exit_code == TaskNotFoundError.exit_code


# ---------------------------------------------------------------------------
# Phase 5A — @namespace def _(): ... registers tasks at the root (no prefix)
# ---------------------------------------------------------------------------


class TestUnderscoreRoot:
    """A function named ``_`` decorated with @namespace maps its tasks to the root."""

    def test_underscore_name_uses_root_path(self):
        @task(name="root-task")
        def root_t():
            pass

        @namespace
        def _():
            return [root_t]

        rns = RootNamespace()
        rns.load(_mod(_=_))
        assert "root-task" in rns
        assert "_:root-task" not in rns

    def test_explicit_path_overrides_underscore(self):
        @task(name="t")
        def t():
            pass

        @namespace(path="ns")
        def _():
            return [t]

        rns = RootNamespace()
        rns.load(_mod(_=_))
        assert "ns:t" in rns
        assert "t" not in rns

    def test_non_underscore_name_uses_function_name(self):
        @task(name="t")
        def t():
            pass

        @namespace
        def tools():
            return [t]

        rns = RootNamespace()
        rns.load(_mod(tools=tools))
        assert "tools:t" in rns
        assert "t" not in rns

    def test_explicit_empty_path_also_registers_at_root(self):
        """path="" still works explicitly (backward-compat)."""

        @task(name="root-task")
        def root_t():
            pass

        @namespace(path="")
        def anything():
            return [root_t]

        rns = RootNamespace()
        rns.load(_mod(anything=anything))
        assert "root-task" in rns


# ---------------------------------------------------------------------------
# Phase 5B — lazy factory: body not executed until .items() is first called
# ---------------------------------------------------------------------------


class TestLazyNamespaceFactory:
    """The factory function body is NOT called at decoration time."""

    def test_factory_not_called_at_decoration_time(self):
        calls: list[int] = []

        @namespace
        def ns():
            calls.append(1)
            return []

        assert calls == []

    def test_factory_called_on_first_items_access(self):
        calls: list[int] = []

        @task(name="t")
        def t():
            pass

        @namespace
        def ns():
            calls.append(1)
            return [t]

        rns = RootNamespace()
        rns.load(_mod(ns=ns))
        assert calls == []  # load() is shallow — factory not yet called
        assert "ns:t" in rns  # triggers resolution
        assert calls == [1]

    def test_factory_called_only_once(self):
        calls: list[int] = []

        @task(name="t")
        def t():
            pass

        @namespace
        def ns():
            calls.append(1)
            return [t]

        # Access items() twice directly
        ns.items()
        ns.items()
        assert len(calls) == 1

    def test_factory_returning_list(self):
        @task(name="t")
        def t():
            pass

        @namespace(path="grp")
        def grp():
            return [t]

        rns = RootNamespace()
        rns.load(_mod(grp=grp))
        assert "grp:t" in rns

    def test_factory_returning_dict(self):
        @task(name="migrate")
        def migrate():
            pass

        @namespace(path="db")
        def db():
            return {"": [migrate]}

        rns = RootNamespace()
        rns.load(_mod(db=db))
        assert "db:migrate" in rns

    def test_factory_returning_single_task(self):
        @task(name="lone")
        def lone():
            pass

        @namespace(path="grp")
        def grp():
            return lone  # single task, not wrapped in a list

        rns = RootNamespace()
        rns.load(_mod(grp=grp))
        assert "grp:lone" in rns

    def test_factory_returning_single_module(self):
        @task(name="mod-task")
        def mod_task():
            pass

        mod = types.ModuleType("fake")
        mod.__dict__["mod_task"] = mod_task

        @namespace(path="m")
        def m():
            return mod  # single module, not wrapped in a list

        rns = RootNamespace()
        rns.load(_mod(m=m))
        assert "m:mod-task" in rns

    def test_factory_returning_tuple(self):
        @task(name="a")
        def a():
            pass

        @task(name="b")
        def b():
            pass

        @namespace(path="tup")
        def tup():
            return (a, b)  # tuple, not a list

        rns = RootNamespace()
        rns.load(_mod(tup=tup))
        assert "tup:a" in rns
        assert "tup:b" in rns

    def test_factory_returning_generator(self):
        @task(name="g")
        def g():
            pass

        @namespace(path="gen")
        def gen():
            yield g  # generator

        rns = RootNamespace()
        rns.load(_mod(gen=gen))
        assert "gen:g" in rns

    def test_mapping_and_factory_both_raises(self):
        with pytest.raises(ValueError, match="not both"):
            Namespace(mapping={}, factory=lambda: [])


# ---------------------------------------------------------------------------
# Phase 5C — shallow load + on-demand resolution
# ---------------------------------------------------------------------------


class TestShallowLoad:
    """load() registers Task objects immediately; Namespace objects are deferred."""

    def test_direct_task_registered_without_resolution(self):
        @task(name="t")
        def t():
            pass

        rns = RootNamespace()
        rns.load(_mod(t=t))
        # Task is in _mappings directly; no pending work queued
        assert "t" in rns._mappings
        assert not rns._pending

    def test_namespace_deferred_on_load(self):
        @task(name="t")
        def t():
            pass

        @namespace
        def ci():
            return [t]

        rns = RootNamespace()
        rns.load(_mod(ci=ci))
        # Task is NOT yet in _mappings; namespace is in _pending
        assert "ci:t" not in rns._mappings
        assert "ci" in rns._pending

    def test_accessing_key_resolves_only_matching_prefix(self):
        @task(name="build")
        def build():
            pass

        @task(name="push")
        def push():
            pass

        @namespace
        def ci():
            return [build]

        @namespace
        def deploy():
            return [push]

        rns = RootNamespace()
        rns.load(_mod(ci=ci, deploy=deploy))
        # Access a "ci:" key — only "ci" should be resolved
        assert "ci:build" in rns
        assert "ci" not in rns._pending  # ci is now resolved
        assert "deploy" in rns._pending  # deploy is still pending

    def test_underscore_namespace_resolved_for_root_task(self):
        @task(name="hello")
        def hello():
            pass

        @namespace
        def _():
            return [hello]

        rns = RootNamespace()
        rns.load(_mod(_=_))
        # "" key in _pending because @namespace def _() → path=""
        assert "hello" in rns
