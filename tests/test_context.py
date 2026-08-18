"""Tests for ClakContext attached during dispatch."""

import pytest

from clak import Argument, Command, Parser
from clak.core.context import ClakContext
from clak.runtime.settings import ClakSettings

pytestmark = pytest.mark.tags("unit-tests")


def test_ctx_is_clak_context_with_settings():
    seen = {}

    class App(Parser):
        def cli_run(self, ctx, **_):
            seen["ctx"] = ctx
            seen["type"] = type(ctx)
            return None

    App(parse=False).dispatch([])
    ctx = seen["ctx"]
    assert isinstance(ctx, ClakContext)
    assert seen["type"] is ClakContext
    assert isinstance(ctx.settings, ClakSettings)
    assert ctx.cli_self is not None
    assert ctx.cli_root is not None
    assert ctx.runtime is not None
    assert ctx.facts is not None
    assert ctx.args is not None
    assert isinstance(ctx.plugins, dict)
    assert isinstance(ctx.data, dict)
    assert "runtime" in ctx.as_kwargs()


def test_ctx_is_one_instance_mutated_down_hierarchy():
    seen = {}

    class Child(Parser):
        def cli_run(self, ctx, **_):
            seen["child_ctx"] = ctx
            seen["child_first"] = ctx.cli_first
            seen["child_id"] = id(ctx)

    class App(Parser):
        def cli_group(self, ctx, **_):
            seen["root_ctx"] = ctx
            seen["root_first"] = ctx.cli_first
            seen["root_id"] = id(ctx)

        child = Command(Child)

    App(parse=False).dispatch(["child"])
    assert seen["root_id"] == seen["child_id"]
    assert seen["root_first"] is True
    assert seen["child_first"] is False
    assert seen["root_ctx"] is seen["child_ctx"]


def test_cli_group_receives_unpacked_context_kwargs():
    seen = {}

    class App(Parser):
        name_arg = Argument("--label", default="x")

        def cli_group(self, ctx, cli_root=None, runtime=None, **_):
            seen["cli_root"] = cli_root
            seen["runtime"] = runtime
            seen["ctx"] = ctx

        def cli_run(self, **_):
            return None

    app = App(parse=False)
    app.dispatch([])
    assert seen["ctx"] is app._clak_ctx
    assert seen["cli_root"] is app
    assert seen["runtime"] is seen["ctx"].runtime
