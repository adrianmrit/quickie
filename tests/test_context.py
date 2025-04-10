from collections import ChainMap


class TestContext:
    def test_copy(self, context):
        context_copy = context.copy()
        assert context is not context_copy
        assert context.cwd == context_copy.cwd
        assert context.env == context_copy.env
        assert isinstance(context.env, ChainMap)
