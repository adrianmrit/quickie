from frozendict import frozendict


class TestContext:
    def test_copy(self, context):
        context_copy = context.copy()
        assert context is not context_copy
        assert context.cwd == context_copy.cwd
        assert context.env is context_copy.env
        assert isinstance(context.env, frozendict)
        assert context.stdin is context_copy.stdin
        assert context.stdout is context_copy.stdout
        assert context.stderr is context_copy.stderr
