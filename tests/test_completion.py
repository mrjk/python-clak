"""Tests for completion script generation."""

import pytest

from clak import CompCmdRender, CompRenderOptMixin, Parser

pytestmark = pytest.mark.tags("unit-tests")


def test_comp_cmd_render_emits_shellcode(capsys):
    """CompCmdRender prints argcomplete shellcode."""

    class App(CompCmdRender):
        pass

    App(parse=False, add_help=False).dispatch(["--shell", "bash"])
    out = capsys.readouterr().out
    assert out
    assert "complete" in out.lower() or "argcomplete" in out.lower()


def test_comp_render_opt_mixin_exposes_completion_not_shell():
    """--completion is the only extra flag; --shell lives on CompCmdRender."""

    class App(CompRenderOptMixin, Parser):
        def cli_run(self, **_):
            return None

    flags = {
        opt
        for action in App(parse=False, add_help=False).parser._actions
        for opt in action.option_strings
    }
    assert "--completion" in flags
    assert "--shell" not in flags
