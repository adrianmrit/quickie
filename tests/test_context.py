from collections import ChainMap
from quickie.context import Context


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
