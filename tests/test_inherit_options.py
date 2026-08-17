"""Tests for ancestor flag propagation onto descendants."""

# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods

import argparse

import pytest

from clak import Arg, Command, Opt, Parser

pytestmark = pytest.mark.tags("unit-tests")


def _app_with_grep():
    class Grep(Parser):
        pattern = Arg("pattern")
        files = Arg("files", nargs="*")

        def cli_run(self, **_):
            return None

    class App(Parser):
        verbose = Opt("--verbose", action="store_true", help="Verbose mode")
        config = Opt("--config", help="Config file")
        grep = Command(Grep, help="Search files")

        def cli_run(self, **_):
            return None

    return App


def test_flag_after_subcommand():
    """Ancestor flags are valid after the subcommand name."""
    app = _app_with_grep()(parse=False, add_help=False)
    args = app.parse_args(["grep", "--verbose", "foo"])
    assert args.verbose is True
    assert args.pattern == "foo"


def test_flag_before_subcommand_not_overwritten():
    """Parent value survives when the leaf copy uses SUPPRESS."""
    app = _app_with_grep()(parse=False, add_help=False)
    args = app.parse_args(["--verbose", "grep", "foo"])
    assert args.verbose is True
    assert args.pattern == "foo"


def test_both_placements_last_wins():
    """Same dest: later token on the command line wins."""
    app = _app_with_grep()(parse=False, add_help=False)
    args = app.parse_args(["--config", "a", "grep", "--config", "b", "foo"])
    assert args.config == "b"
    assert args.pattern == "foo"


def test_closer_ancestor_copied_not_root():
    """Leaf copies intermediate's --verbose, not root's."""

    class Leaf(Parser):
        def cli_run(self, **_):
            return None

    class Db(Parser):
        verbose = Opt("--verbose", action="store_true", help="db verbose")
        migrate = Command(Leaf, help="Migrate")

        def cli_run(self, **_):
            return None

    class App(Parser):
        verbose = Opt("--verbose", action="store_true", help="root verbose")
        db = Command(Db, help="Database")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=True)
    help_text = app.children["db"].children["migrate"].parser.format_help()
    assert "parent options:" in help_text
    assert "db verbose" in help_text
    assert "root verbose" not in help_text


def test_intermediate_shadow_does_not_reset_root_value():
    """Inner local --verbose uses SUPPRESS so an earlier root flag stays set."""

    class Leaf(Parser):
        def cli_run(self, **_):
            return None

    class Db(Parser):
        verbose = Opt("--verbose", action="store_true", help="db verbose")
        migrate = Command(Leaf, help="Migrate")

        def cli_run(self, **_):
            return None

    class App(Parser):
        verbose = Opt("--verbose", action="store_true", help="root verbose")
        db = Command(Db, help="Database")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=False)
    args = app.parse_args(["--verbose", "db", "migrate"])
    assert args.verbose is True


def test_positionals_not_inherited():
    """Ancestor positionals are not copied onto siblings."""

    class Mid(Parser):
        path = Arg("path")

        def cli_run(self, **_):
            return None

    class Other(Parser):
        def cli_run(self, **_):
            return None

    class App(Parser):
        mid = Command(Mid, help="Mid")
        other = Command(Other, help="Other")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=True)
    usage = app.children["other"].parser.format_usage()
    assert "path" not in usage.lower()
    with pytest.raises(argparse.ArgumentError):
        app.parse_args(["other", "somewhere"])


def test_mid_level_flag_on_grandchild_not_sibling():
    """A mid-level flag is copied to its descendants only."""

    class Migrate(Parser):
        def cli_run(self, **_):
            return None

    class Status(Parser):
        def cli_run(self, **_):
            return None

    class Db(Parser):
        lock = Opt("--lock", action="store_true")
        migrate = Command(Migrate, help="Migrate")

        def cli_run(self, **_):
            return None

    class App(Parser):
        verbose = Opt("--verbose", action="store_true")
        db = Command(Db, help="Database")
        status = Command(Status, help="Status")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=False)
    args = app.parse_args(["db", "migrate", "--lock", "--verbose"])
    assert args.lock is True
    assert args.verbose is True

    args = app.parse_args(["status", "--verbose"])
    assert args.verbose is True

    with pytest.raises(argparse.ArgumentError, match="unrecognized arguments"):
        app.parse_args(["status", "--lock"])


def test_reused_class_under_two_roots():
    """Each tree only inherits flags from that instance's ancestors."""

    class Vars(Parser):
        def cli_run(self, **_):
            return None

    class App(Parser):
        vars = Command(Vars, help="Vars")

        def cli_run(self, **_):
            return None

    class Psf(Parser):
        verbose = Opt("--verbose", action="store_true")
        app = Command(App, help="App")

        def cli_run(self, **_):
            return None

    class Paasify(Parser):
        trace = Opt("--trace", action="store_true")
        app = Command(App, help="App")

        def cli_run(self, **_):
            return None

    psf = Psf(parse=False, add_help=False)
    paasify = Paasify(parse=False, add_help=False)

    args = psf.parse_args(["app", "vars", "--verbose"])
    assert args.verbose is True
    with pytest.raises(argparse.ArgumentError, match="unrecognized arguments"):
        psf.parse_args(["app", "vars", "--trace"])

    args = paasify.parse_args(["app", "vars", "--trace"])
    assert args.trace is True
    with pytest.raises(argparse.ArgumentError, match="unrecognized arguments"):
        paasify.parse_args(["app", "vars", "--verbose"])


def test_propagate_opt_out():
    """Meta.propagate_options = False restores leftover errors."""

    class Grep(Parser):
        class Meta:
            propagate_options = False

        pattern = Arg("pattern")

        def cli_run(self, **_):
            return None

    class App(Parser):
        verbose = Opt("--verbose", action="store_true")
        grep = Command(Grep, help="Search")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=False)
    with pytest.raises(argparse.ArgumentError, match="unrecognized arguments"):
        app.parse_args(["grep", "--verbose", "foo"])
    args = app.parse_args(["--verbose", "grep", "foo"])
    assert args.verbose is True
    assert args.pattern == "foo"


def test_leaf_help_parent_options_group():
    """Inherited flags sit under parent options:, not the leaf's own groups."""

    class Grep(Parser):
        pattern = Arg("pattern")
        fmt = Opt("--format", option_group="Output options", help="Format")

        def cli_run(self, **_):
            return None

    class App(Parser):
        verbose = Opt(
            "--verbose",
            action="store_true",
            option_group="Output options",
            help="Verbose mode",
        )
        grep = Command(Grep, help="Search")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=True)
    help_text = app.children["grep"].parser.format_help()
    assert "parent options:" in help_text
    parent_idx = help_text.index("parent options:")
    output_idx = help_text.index("Output options:")
    assert "--verbose" in help_text[parent_idx:]
    assert "--format" in help_text[output_idx:parent_idx]
    assert "--verbose" not in help_text[output_idx:parent_idx]


def test_root_help_has_no_parent_options_group():
    """Root --help has no parent options: section."""
    app = _app_with_grep()(parse=False, add_help=True)
    help_text = app.parser.format_help()
    assert "parent options:" not in help_text
    assert "--verbose" in help_text


def test_exit_action_propagates_by_default():
    """An exit-style argparse action still copies unless propagate=False."""

    class Leaf(Parser):
        def cli_run(self, **_):
            return None

    class App(Parser):
        about = Opt("--about", action="version", version="1.2.3")
        leaf = Command(Leaf, help="Leaf")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=False)
    help_text = app.children["leaf"].parser.format_help()
    assert "parent options:" in help_text
    assert "--about" in help_text[help_text.index("parent options:") :]
    with pytest.raises(SystemExit) as exc:
        app.parse_args(["leaf", "--about"])
    assert exc.value.code in (0, None)


def test_propagate_false_not_copied():
    """propagate=False keeps the flag on the defining parser only."""

    class Leaf(Parser):
        def cli_run(self, **_):
            return None

    class App(Parser):
        quiet = Opt("--quiet", action="store_true", propagate=False)
        verbose = Opt("--verbose", action="store_true")
        leaf = Command(Leaf, help="Leaf")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=False)
    args = app.parse_args(["--quiet", "leaf"])
    assert args.quiet is True
    with pytest.raises(argparse.ArgumentError, match="unrecognized arguments"):
        app.parse_args(["leaf", "--quiet"])
    args = app.parse_args(["leaf", "--verbose"])
    assert args.verbose is True


def test_intermixed_inherited_flag_among_positionals():
    """Inherited flags mix with leaf nargs=* when intermixed is on."""
    app = _app_with_grep()(parse=False, add_help=False)
    args = app.parse_args(["grep", "foo", "--verbose", "bar"])
    assert args.pattern == "foo"
    assert args.verbose is True
    assert args.files == ["bar"]
