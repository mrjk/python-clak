"""Tests for view dispatch, example scripts, and core view classes."""

import logging

import pytest

from clak import Parser, ParserNode
from clak.comp.views import ListViewMixin
from clak.views import ListView, PprintView, ShowView
from tests.view_fixtures import USERS, _option_flags

pytestmark = pytest.mark.tags("unit-tests")


# ---------------------------------------------------------------------------
# Core views (no mixin)
# ---------------------------------------------------------------------------


def test_show_view_prints_and_returns_rendered_text(capsys):
    rendered = ShowView({"name": "World"}).render()

    assert "World" in rendered
    assert rendered in capsys.readouterr().out


def test_list_view_forwards_options_for_heterogeneous_rows():
    rendered = ListView(
        [{"name": "World"}, {"age": 42}],
        columns=["name", "age"],
        add_index=True,
    ).render(stdout=False)

    assert "Index" in rendered
    assert "World" in rendered
    assert "42" in rendered
    assert "-" in rendered


def test_pprint_view_can_render_without_stdout(capsys):
    rendered = PprintView({"name": "World"}).render(stdout=False)

    assert "World" in rendered
    assert capsys.readouterr().out == ""


def test_dispatch_renders_returned_view(capsys):
    parser = ParserNode()
    parser.cli_run = lambda **_: ShowView({"name": "World"})

    result = parser.dispatch([])

    assert isinstance(result, ShowView)
    assert "World" in capsys.readouterr().out


def test_dispatch_supports_configured_view_class(capsys):
    parser = ParserNode()
    parser.meta__cli_view = ShowView
    parser.cli_run = lambda **_: {"name": "World"}

    result = parser.dispatch([])

    assert result == {"name": "World"}
    assert "World" in capsys.readouterr().out


def test_no_mixin_raw_return_is_silent(capsys):
    class App(Parser):
        def cli_run(self, **_):
            return {"name": "World"}

    result = App(parse=False, add_help=False).dispatch([])

    assert result == {"name": "World"}
    assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# Mixins — explicit view + CLI override
# ---------------------------------------------------------------------------


def test_explicit_view_still_works_with_mixin_and_cli_override(capsys, caplog):
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return ListView(USERS, columns=["name", "role"])

    with caplog.at_level(logging.INFO):
        App(parse=False, add_help=False).dispatch(["--columns", "name"])

    out = capsys.readouterr().out
    assert "ada" in out
    assert "admin" not in out
    assert "overrides view setting" in caplog.text


def test_example_script_exceptions_runs(capsys):
    """Smoke-test the documented exception-handling example."""
    import importlib.util
    import sys
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "examples" / "script_exceptions.py"
    spec = importlib.util.spec_from_file_location("script_exceptions_example", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    with pytest.raises(SystemExit) as exc:
        module.AppMain(parse=False, add_help=False).dispatch(["deploy", "missing"])
    assert exc.value.code == 44
    assert "not found" in capsys.readouterr().err


def test_example_script_views_runs(capsys):
    """Smoke-test the documented example module."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "examples" / "script_views.py"
    spec = importlib.util.spec_from_file_location("script_views_example", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    module.AppMain(parse=False, add_help=False).dispatch(["--columns", "name,role"])

    out = capsys.readouterr().out
    assert "ada" in out
    assert "admin" in out
    assert "London" not in out
