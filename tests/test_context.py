from frozendict import frozendict

from task_mom.context import Context, GlobalContext


class TestGlobalContext:
    def test_singleton(self):
        assert GlobalContext() is GlobalContext()
        assert GlobalContext.get() is GlobalContext()
        assert isinstance(GlobalContext.get(), Context)


class TestContext:
    def test_copy(self):
        context = Context()
        context_copy = context.copy()
        assert context is not context_copy
        assert context.cwd == context_copy.cwd
        assert context.env is context_copy.env
        assert isinstance(context.env, frozendict)
        assert context.stdin is context_copy.stdin
        assert context.stdout is context_copy.stdout
        assert context.stderr is context_copy.stderr
