"""Tests for RichHelpMixin and help formatter selection."""

# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods

import re
import sys

import pytest

from clak import Command, Parser, RecursiveHelpFormatter, RichHelpMixin
from clak.comp.help import _HELP_HIGHLIGHTS, RichRecursiveHelpFormatter
from clak.core.argparse_ import RecursiveHelpFormatter as CoreRecursiveHelpFormatter
from clak.runtime.settings import CLAK_COLOR_BACKEND_ENV
from clak.views.base import strip_ansi
from tests.view_fixtures import _has_background_csi

pytestmark = pytest.mark.tags("unit-tests")


def _force_help_color(monkeypatch):
    pytest.importorskip("rich")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("clak.comp.help.CLAK_COLORS", True)
    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "auto")


class _PlainApp(Parser):
    """Demo help."""

    def cli_run(self, **_):
        return None


class _RichApp(RichHelpMixin, Parser):
    """Demo help."""

    def cli_run(self, **_):
        return None


def test_plain_parser_uses_recursive_formatter():
    """Default Parser keeps RecursiveHelpFormatter and no ANSI."""
    app = _PlainApp(parse=False, add_help=True)
    assert app.get_help_formatter_class() is RecursiveHelpFormatter
    assert app.parser.formatter_class is RecursiveHelpFormatter
    assert "\x1b[" not in app.parser.format_help()


def test_mixin_non_tty_matches_plain():
    plain = _PlainApp(parse=False, add_help=True).parser.format_help()
    rich_help = _RichApp(parse=False, add_help=True).parser.format_help()
    assert rich_help == plain
    assert "\x1b[" not in rich_help


def test_mixin_forced_color_has_ansi(monkeypatch):
    _force_help_color(monkeypatch)
    help_text = _RichApp(parse=False, add_help=True).parser.format_help()
    assert "\x1b[" in help_text
    assert not _has_background_csi(help_text)
    stripped = strip_ansi(help_text)
    assert "usage:" in stripped
    assert "-h" in stripped or "--help" in stripped


def test_mixin_markup_description_and_epilog(monkeypatch):
    _force_help_color(monkeypatch)

    class App(RichHelpMixin, Parser):
        class Meta:
            help_description = "Hello [bold]World[/bold]"
            help_epilog = "See [cyan]docs[/cyan]"

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "[bold]" not in help_text
    assert "[cyan]" not in help_text
    assert "World" in help_text
    assert "docs" in help_text
    assert "\x1b[" in help_text


def test_mixin_markup_stays_literal_without_tty():
    class App(RichHelpMixin, Parser):
        class Meta:
            help_description = "Hello [bold]World[/bold]"
            help_epilog = "See [cyan]docs[/cyan]"

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "[bold]World[/bold]" in help_text
    assert "[cyan]docs[/cyan]" in help_text
    assert "\x1b[" not in help_text


def test_root_mixin_applies_to_child_parser():
    class Child(Parser):
        def cli_run(self, **_):
            return None

    class Root(RichHelpMixin, Parser):
        child = Command(Child, help="Run child")

        def cli_run(self, **_):
            return None

    app = Root(parse=False, add_help=True)
    assert app.parser.formatter_class is RichRecursiveHelpFormatter
    assert app.children["child"].parser.formatter_class is RichRecursiveHelpFormatter
    assert (
        app.children["child"].get_help_formatter_class() is RichRecursiveHelpFormatter
    )


def test_child_meta_opts_out_of_rich_formatter():
    class Child(Parser):
        class Meta:
            help_formatter = RecursiveHelpFormatter

        def cli_run(self, **_):
            return None

    class Root(RichHelpMixin, Parser):
        child = Command(Child, help="Run child")

        def cli_run(self, **_):
            return None

    app = Root(parse=False, add_help=True)
    assert app.parser.formatter_class is RichRecursiveHelpFormatter
    assert app.children["child"].parser.formatter_class is RecursiveHelpFormatter


def test_mixin_color_backend_none_is_plain(monkeypatch):
    pytest.importorskip("rich")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("clak.comp.help.CLAK_COLORS", True)
    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "none")
    help_text = _RichApp(parse=False, add_help=True).parser.format_help()
    assert help_text == _PlainApp(parse=False, add_help=True).parser.format_help()
    assert "\x1b[" not in help_text


def test_mixin_clak_colors_off_is_plain(monkeypatch):
    pytest.importorskip("rich")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("clak.comp.help.CLAK_COLORS", False)
    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "auto")
    help_text = _RichApp(parse=False, add_help=True).parser.format_help()
    assert help_text == _PlainApp(parse=False, add_help=True).parser.format_help()
    assert "\x1b[" not in help_text


def test_mixin_colored_command_tree(monkeypatch):
    _force_help_color(monkeypatch)

    class Child(Parser):
        def cli_run(self, **_):
            return None

    class Root(RichHelpMixin, Parser):
        """Root with a child."""

        child = Command(Child, help="Run child")

        def cli_run(self, **_):
            return None

    help_text = Root(parse=False, add_help=True).parser.format_help()
    stripped = strip_ansi(help_text)
    assert "subcommands:" in stripped
    assert "child" in stripped
    assert "Run child" in stripped
    assert "\x1b[" in help_text


def test_help_highlight_headers_multiline():
    """Section titles match after the first line (MULTILINE)."""
    text = "usage: app [-h]\n\noptions:\n  -h, --help\n"
    groups = []
    for pattern in _HELP_HIGHLIGHTS:
        if "?P<groups>" not in pattern:
            continue
        groups.extend(match.group("groups") for match in re.finditer(pattern, text))
    assert "usage:" in groups
    assert "options:" in groups


def test_help_highlight_skips_prose_flags():
    """``--flag`` in description prose is not treated as an option name."""
    text = (
        "usage: app [-h]\n"
        "\n"
        "Use --force to continue.\n"
        "\n"
        "options:\n"
        "  -h, --help            show this help message and exit\n"
        "  --config CONFIG, -c CONFIG  path\n"
    )
    args_pattern = next(p for p in _HELP_HIGHLIGHTS if "?P<args>" in p)
    found = [match.group("args") for match in re.finditer(args_pattern, text)]
    joined = " ".join(found)
    assert "--force" not in joined
    assert any("-h" in item for item in found)
    assert any("--config" in item for item in found)


def test_recursive_help_formatter_exported_from_clak():
    assert RecursiveHelpFormatter is CoreRecursiveHelpFormatter
