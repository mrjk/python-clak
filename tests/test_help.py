"""Tests for default Rich help formatter and opt-out."""

# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods,protected-access

import re
import sys

import pytest

from clak import Argument, Command, Parser, RecursiveHelpFormatter, RichHelpMixin
from clak.comp.help import _HELP_HIGHLIGHTS, RichRecursiveHelpFormatter
from clak.core.argparse_ import RecursiveHelpFormatter as CoreRecursiveHelpFormatter
from clak.runtime.settings import CLAK_COLOR_BACKEND_ENV
from clak.views.base import strip_ansi
from tests.view_fixtures import _has_background_csi

pytestmark = pytest.mark.tags("unit-tests")


def _force_help_color(monkeypatch):
    pytest.importorskip("rich")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("clak.comp.help.CLAK_COLORS", True)
    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "auto")


class _DefaultApp(Parser):
    """Demo help."""

    def cli_run(self, **_):
        return None


class _OptOutApp(Parser):
    """Demo help."""

    class Meta:
        help_formatter = RecursiveHelpFormatter

    def cli_run(self, **_):
        return None


class _MixinApp(RichHelpMixin, Parser):
    """Demo help."""

    def cli_run(self, **_):
        return None


def test_default_parser_uses_rich_formatter():
    """Default Parser uses RichRecursiveHelpFormatter; no ANSI without TTY."""
    app = _DefaultApp(parse=False, add_help=True)
    assert app.get_help_formatter_class() is RichRecursiveHelpFormatter
    assert app.parser.formatter_class is RichRecursiveHelpFormatter
    assert "\x1b[" not in app.parser.format_help()


def test_opt_out_tty_has_no_ansi(monkeypatch):
    """Argparse 3.14 TTY color stays off; Clak owns help color."""
    pytest.importorskip("rich")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("clak.comp.help.CLAK_COLORS", True)
    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "auto")
    help_text = _OptOutApp(parse=False, add_help=True).parser.format_help()
    assert "\x1b[" not in help_text


def test_non_tty_matches_opt_out():
    default_help = _DefaultApp(parse=False, add_help=True).parser.format_help()
    opt_out = _OptOutApp(parse=False, add_help=True).parser.format_help()
    mixin_help = _MixinApp(parse=False, add_help=True).parser.format_help()
    assert default_help == opt_out
    assert mixin_help == opt_out
    assert "\x1b[" not in default_help


def test_forced_color_has_ansi(monkeypatch):
    _force_help_color(monkeypatch)
    help_text = _DefaultApp(parse=False, add_help=True).parser.format_help()
    assert "\x1b[" in help_text
    assert not _has_background_csi(help_text)
    stripped = strip_ansi(help_text)
    assert "usage:" in stripped
    assert "-h" in stripped or "--help" in stripped


def test_mixin_forced_color_matches_default(monkeypatch):
    _force_help_color(monkeypatch)
    default_help = _DefaultApp(parse=False, add_help=True).parser.format_help()
    mixin_help = _MixinApp(parse=False, add_help=True).parser.format_help()
    assert mixin_help == default_help
    assert "\x1b[" in mixin_help


def test_markup_description_and_epilog(monkeypatch):
    _force_help_color(monkeypatch)

    class App(Parser):
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


def test_markup_stays_literal_without_tty():
    class App(Parser):
        class Meta:
            help_description = "Hello [bold]World[/bold]"
            help_epilog = "See [cyan]docs[/cyan]"

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "[bold]World[/bold]" in help_text
    assert "[cyan]docs[/cyan]" in help_text
    assert "\x1b[" not in help_text


def test_default_applies_to_child_parser():
    class Child(Parser):
        def cli_run(self, **_):
            return None

    class Root(Parser):
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

    class Root(Parser):
        child = Command(Child, help="Run child")

        def cli_run(self, **_):
            return None

    app = Root(parse=False, add_help=True)
    assert app.parser.formatter_class is RichRecursiveHelpFormatter
    assert app.children["child"].parser.formatter_class is RecursiveHelpFormatter


def test_mixin_reopts_child_after_parent_opt_out():
    class Child(RichHelpMixin, Parser):
        def cli_run(self, **_):
            return None

    class Root(Parser):
        class Meta:
            help_formatter = RecursiveHelpFormatter

        child = Command(Child, help="Run child")

        def cli_run(self, **_):
            return None

    app = Root(parse=False, add_help=True)
    assert app.parser.formatter_class is RecursiveHelpFormatter
    assert app.children["child"].parser.formatter_class is RichRecursiveHelpFormatter


def test_color_backend_none_is_plain(monkeypatch):
    pytest.importorskip("rich")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("clak.comp.help.CLAK_COLORS", True)
    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "none")
    help_text = _DefaultApp(parse=False, add_help=True).parser.format_help()
    assert help_text == _OptOutApp(parse=False, add_help=True).parser.format_help()
    assert "\x1b[" not in help_text


def test_clak_colors_off_is_plain(monkeypatch):
    pytest.importorskip("rich")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("clak.comp.help.CLAK_COLORS", False)
    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "auto")
    help_text = _DefaultApp(parse=False, add_help=True).parser.format_help()
    assert help_text == _OptOutApp(parse=False, add_help=True).parser.format_help()
    assert "\x1b[" not in help_text


def test_no_color_is_plain(monkeypatch):
    pytest.importorskip("rich")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("clak.comp.help.CLAK_COLORS", True)
    monkeypatch.setenv(CLAK_COLOR_BACKEND_ENV, "auto")
    help_text = _DefaultApp(parse=False, add_help=True).parser.format_help()
    assert help_text == _OptOutApp(parse=False, add_help=True).parser.format_help()
    assert "\x1b[" not in help_text


def test_colored_command_tree(monkeypatch):
    _force_help_color(monkeypatch)

    class Child(Parser):
        def cli_run(self, **_):
            return None

    class Root(Parser):
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


def _leaf_parser():
    class Leaf(Parser):
        def cli_run(self, **_):
            return None

    return Leaf


def test_ungrouped_commands_keep_single_subcommands_list():
    """No command_group on any child: today's single subcommands: list."""

    class Child(Parser):
        def cli_run(self, **_):
            return None

    class Root(Parser):
        alpha = Command(Child, help="First")
        beta = Command(Child, help="Second")

        def cli_run(self, **_):
            return None

    help_text = Root(parse=False, add_help=True).parser.format_help()
    assert help_text.count("subcommands:") == 1
    assert "subcommands (base):" not in help_text
    assert "alpha" in help_text
    assert "beta" in help_text
    assert "positional arguments:" not in help_text


def test_empty_positional_arguments_heading_hidden():
    """No real positionals: drop the empty positional arguments: heading."""
    leaf = _leaf_parser()

    class App(Parser):
        child = Command(leaf, help="A child")

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "positional arguments:" not in help_text
    assert "subcommands:" in help_text


def test_real_positionals_keep_heading():
    """A NAME positional still gets the positional arguments: section."""

    class App(Parser):
        name = Argument("NAME", help="Who")

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "positional arguments:" in help_text
    assert "NAME" in help_text


def test_positionals_and_subcommands_keep_heading():
    leaf = _leaf_parser()

    class App(Parser):
        name = Argument("NAME", help="Who")
        child = Command(leaf, help="A child")

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "positional arguments:" in help_text
    assert "NAME" in help_text
    assert "subcommands:" in help_text
    pos_idx = help_text.index("positional arguments:")
    sub_idx = help_text.index("subcommands:")
    assert pos_idx < sub_idx
    assert "NAME" in help_text[pos_idx:sub_idx]


def test_command_groups_named_and_leftover():
    """Named Meta sections, empty key omitted, ungrouped leftover subcommands:."""
    leaf = _leaf_parser()

    class App(Parser):
        class Meta:
            command_groups = (
                ("base", "subcommands (base):"),
                ("empty", "subcommands (empty):"),
                ("dynamic", "subcommands (dynamic):"),
            )

        tool = Command(leaf, command_group="base", help="Tools")
        render = Command(leaf, command_group="dynamic", help="Render")
        orphan = Command(leaf, help="Leftover")

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "subcommands (base):" in help_text
    assert "subcommands (dynamic):" in help_text
    assert "subcommands (empty):" not in help_text
    assert help_text.count("subcommands:") == 1
    base_idx = help_text.index("subcommands (base):")
    dynamic_idx = help_text.index("subcommands (dynamic):")
    leftover_idx = help_text.index("\nsubcommands:\n")
    assert base_idx < dynamic_idx < leftover_idx
    assert help_text.index("tool", base_idx) < dynamic_idx
    assert help_text.index("render", dynamic_idx) < leftover_idx
    assert leftover_idx < help_text.index("orphan", leftover_idx)


def test_command_group_unknown_key_after_named():
    """Keys not in Meta.command_groups become {key}: after named sections."""
    leaf = _leaf_parser()

    class App(Parser):
        class Meta:
            command_groups = (("base", "subcommands (base):"),)

        tool = Command(leaf, command_group="base", help="Tools")
        extra = Command(leaf, command_group="extra", help="Unknown key")
        orphan = Command(leaf, help="Leftover")

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    base_idx = help_text.index("subcommands (base):")
    extra_idx = help_text.index("\nextra:\n")
    leftover_idx = help_text.index("\nsubcommands:\n")
    assert base_idx < extra_idx < leftover_idx
    after_title = help_text[extra_idx + len("\nextra:\n") :]
    assert after_title.lstrip().startswith("extra")


def test_command_groups_do_not_inherit_to_child():
    """Grouping is per-command; a child without Meta keeps subcommands:."""
    leaf_cls = _leaf_parser()

    class ToolGroup(Parser):
        leaf = Command(leaf_cls, help="A leaf")

        def cli_run(self, **_):
            return None

    class Root(Parser):
        class Meta:
            command_groups = (("base", "subcommands (base):"),)

        tool = Command(ToolGroup, command_group="base", help="Tools")

        def cli_run(self, **_):
            return None

    app = Root(parse=False, add_help=True)
    root_help = app.parser.format_help()
    child_help = app.children["tool"].parser.format_help()
    assert "subcommands (base):" in root_help
    assert "subcommands (base):" not in child_help
    assert "subcommands:" in child_help
    assert "leaf" in child_help


def test_command_groups_keep_nested_listing():
    """Nested children still list under their parent command when mode is all."""
    leaf_cls = _leaf_parser()

    class ToolGroup(Parser):
        leaf = Command(leaf_cls, help="A leaf")

        def cli_run(self, **_):
            return None

    class Root(Parser):
        class Meta:
            command_groups = (("base", "subcommands (base):"),)
            help_subcommands = "all"

        tool = Command(ToolGroup, command_group="base", help="Tools")

        def cli_run(self, **_):
            return None

    help_text = Root(parse=False, add_help=True).parser.format_help()
    base_idx = help_text.index("subcommands (base):")
    assert "tool leaf" not in help_text
    nested = _nested_leaf_label(1, "leaf")
    assert nested in help_text
    assert help_text.index(nested, base_idx) > base_idx


def _nested_leaf_label(level, dest):
    """Bullet plus two spaces per nesting level, then the leaf name."""
    return f"  {'  ' * level}{dest}"


def _nested_demo_parsers():
    class Sub1(Parser):
        def cli_run(self, **_):
            return None

    class Command1(Parser):
        sub1 = Command(Sub1, help="SubCommand1")

        def cli_run(self, **_):
            return None

    class Command2(Parser):
        def cli_run(self, **_):
            return None

    return Command1, Command2


def test_help_subcommands_default_is_all():
    """Root --help lists nested children with the parent path hidden."""
    command1_cls, command2_cls = _nested_demo_parsers()

    class App(Parser):
        command1 = Command(command1_cls, help="Execute command 1")
        command2 = Command(command2_cls, help="Execute command 2")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=True)
    layout = app.subparsers._clak_help
    assert layout.subcommands == "all"
    assert layout.hide_parent is True
    assert layout.command_groups == ()
    help_text = app.parser.format_help()
    assert "command1" in help_text
    assert "command2" in help_text
    assert "command1 sub1" not in help_text
    assert _nested_leaf_label(1, "sub1") in help_text
    child_help = app.children["command1"].parser.format_help()
    assert "sub1" in child_help
    assert "SubCommand1" in child_help


def test_help_subcommands_all_hides_parent_path():
    """help_subcommands='all' lists nested leaves with the parent path hidden."""
    command1_cls, command2_cls = _nested_demo_parsers()

    class App(Parser):
        class Meta:
            help_subcommands = "all"

        command1 = Command(command1_cls, help="Execute command 1")
        command2 = Command(command2_cls, help="Execute command 2")

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "command1" in help_text
    assert "command1 sub1" not in help_text
    assert _nested_leaf_label(1, "sub1") in help_text
    assert "command2" in help_text


def test_help_hide_parent_false_keeps_full_paths():
    """help_hide_parent=False keeps flattened nested paths."""
    command1_cls, command2_cls = _nested_demo_parsers()

    class App(Parser):
        class Meta:
            help_subcommands = "all"
            help_hide_parent = False

        command1 = Command(command1_cls, help="Execute command 1")
        command2 = Command(command2_cls, help="Execute command 2")

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "command1 sub1" in help_text


def test_help_hide_parent_aligns_help_column():
    """Nested leaves share the parent help column."""
    leaf_cls = _leaf_parser()

    class ToolGroup(Parser):
        netmap = Command(leaf_cls, help="Map networks")

        def cli_run(self, **_):
            return None

    class App(Parser):
        class Meta:
            help_subcommands = "all"

        tool = Command(ToolGroup, help="Docker helpers")

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    tool_line = next(
        line for line in help_text.splitlines() if "Docker helpers" in line
    )
    netmap_line = next(
        line for line in help_text.splitlines() if "Map networks" in line
    )
    assert "tool netmap" not in help_text
    assert tool_line.index("Docker helpers") == netmap_line.index("Map networks")


def test_help_subcommands_grouped_top_omits_nested():
    """Grouping still works; top mode does not list nested paths."""
    leaf_cls = _leaf_parser()

    class ToolGroup(Parser):
        leaf = Command(leaf_cls, help="A leaf")

        def cli_run(self, **_):
            return None

    class Root(Parser):
        class Meta:
            command_groups = (("base", "subcommands (base):"),)
            help_subcommands = "top"

        tool = Command(ToolGroup, command_group="base", help="Tools")

        def cli_run(self, **_):
            return None

    help_text = Root(parse=False, add_help=True).parser.format_help()
    assert "subcommands (base):" in help_text
    assert "tool" in help_text
    assert "tool leaf" not in help_text
    assert _nested_leaf_label(1, "leaf") not in help_text


def test_help_subcommands_inherited_and_child_override():
    """Root 'all' lists nested paths; a child Meta 'top' does not."""

    class Tip(Parser):
        def cli_run(self, **_):
            return None

    class Leaf(Parser):
        tip = Command(Tip, help="Tip")

        def cli_run(self, **_):
            return None

    class Mid(Parser):
        class Meta:
            help_subcommands = "top"

        leaf = Command(Leaf, help="Leaf")

        def cli_run(self, **_):
            return None

    class Root(Parser):
        class Meta:
            help_subcommands = "all"

        mid = Command(Mid, help="Mid")

        def cli_run(self, **_):
            return None

    app = Root(parse=False, add_help=True)
    root_help = app.parser.format_help()
    assert "mid leaf" not in root_help
    assert _nested_leaf_label(1, "leaf") in root_help
    assert _nested_leaf_label(2, "tip") in root_help
    mid_help = app.children["mid"].parser.format_help()
    assert "leaf" in mid_help
    assert "leaf tip" not in mid_help


def test_help_subcommands_invalid_value_raises():
    class Child(Parser):
        def cli_run(self, **_):
            return None

    class App(Parser):
        class Meta:
            help_subcommands = "tree"

        child = Command(Child, help="A child")

        def cli_run(self, **_):
            return None

    with pytest.raises(ValueError, match="help_subcommands"):
        App(parse=False, add_help=True)


def test_help_hide_parent_invalid_value_raises():
    class Child(Parser):
        def cli_run(self, **_):
            return None

    class App(Parser):
        class Meta:
            help_hide_parent = "yes"

        child = Command(Child, help="A child")

        def cli_run(self, **_):
            return None

    with pytest.raises(ValueError, match="help_hide_parent"):
        App(parse=False, add_help=True)


def test_help_highlight_grouped_subcommand_titles():
    """Parenthetical subcommand section titles match like subcommands:."""
    text = (
        "usage: app [-h]\n"
        "\n"
        "subcommands (base):\n"
        "  tool                 Tools\n"
        "\n"
        "subcommands:\n"
        "  orphan               Orphan\n"
    )
    groups = []
    for pattern in _HELP_HIGHLIGHTS:
        if "?P<groups>" not in pattern:
            continue
        groups.extend(match.group("groups") for match in re.finditer(pattern, text))
    assert "subcommands (base):" in groups
    assert "subcommands:" in groups


def test_grouped_help_forced_color_has_ansi(monkeypatch):
    _force_help_color(monkeypatch)
    leaf = _leaf_parser()

    class App(Parser):
        class Meta:
            command_groups = (("base", "subcommands (base):"),)

        tool = Command(leaf, command_group="base", help="Tools")
        orphan = Command(leaf, help="Leftover")

        def cli_run(self, **_):
            return None

    help_text = App(parse=False, add_help=True).parser.format_help()
    assert "\x1b[" in help_text
    stripped = strip_ansi(help_text)
    assert "subcommands (base):" in stripped
    assert "subcommands:" in stripped
    assert "tool" in stripped
    assert "orphan" in stripped
