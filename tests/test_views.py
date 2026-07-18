"""Tests for public CLI views and parser integration."""

from clak.parser import ParserNode
from clak.views import ListView, PprintView, ShowView


def test_views_print_and_return_rendered_text(capsys):
    view = ShowView({"name": "World"})

    rendered = view.render()

    assert "World" in rendered
    assert rendered in capsys.readouterr().out


def test_list_view_forwards_options_for_heterogeneous_rows():
    view = ListView(
        [{"name": "World"}, {"age": 42}],
        columns=["name", "age"],
        add_index=True,
    )

    rendered = view.render(stdout=False)

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
