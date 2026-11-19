"""Tests for Meta.abbrev_commands / Meta.abbrev_options (prefix matching)."""

# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods

import argparse

import pytest

from clak import Command, Opt, Parser
from clak.core.argp import ArgumentParser, SubParsersAction, format_argument_error

pytestmark = pytest.mark.tags("unit-tests")


def _app(abbrev_commands=None, abbrev_options=None, sub_meta=None):
    """Build ``app sub {buzz,fizz,fizzle}`` with optional Meta values."""

    class Buzz(Parser):
        verbose = Opt("--verbose", action="store_true")

        def cli_run(self, **_):
            return "buzz"

    class Fizz(Parser):
        def cli_run(self, **_):
            return "fizz"

    sub_attrs = {
        "buzz": Command(Buzz),
        "fizz": Command(Fizz),
        "fizzle": Command(Fizz),
    }
    if sub_meta:
        sub_attrs["Meta"] = type("Meta", (), sub_meta)
    Sub = type("Sub", (Parser,), sub_attrs)  # pylint: disable=invalid-name

    meta = {}
    if abbrev_commands is not None:
        meta["abbrev_commands"] = abbrev_commands
    if abbrev_options is not None:
        meta["abbrev_options"] = abbrev_options
    attrs = {"sub": Command(Sub)}
    if meta:
        attrs["Meta"] = type("Meta", (), meta)
    App = type("App", (Parser,), attrs)  # pylint: disable=invalid-name
    return App(parse=False, add_help=False)


def _cmd_path(args):
    args = vars(args)
    return [args[k] for k in sorted(args) if k.startswith("__cli_cmd__")]


def _error(app, argv):
    with pytest.raises(argparse.ArgumentError) as info:
        app.parse_args(argv)
    return format_argument_error(info.value)


# Subcommands
# ========================


def test_commands_not_abbreviated_by_default():
    msg = _error(_app(), ["sub", "bu"])
    assert "unknown command 'bu'" in msg
    assert "did you mean 'buzz'" in msg
    assert "__cli_cmd__" not in msg


def test_unique_prefix_resolves_to_full_name():
    args = _app(abbrev_commands=True).parse_args(["s", "bu"])
    assert _cmd_path(args) == ["sub", "buzz"]
    assert args.__cli_self__.key == "buzz"


def test_exact_name_wins_over_longer_command():
    args = _app(abbrev_commands=True).parse_args(["sub", "fizz"])
    assert _cmd_path(args) == ["sub", "fizz"]


def test_prefix_of_one_longer_command_resolves():
    args = _app(abbrev_commands=True).parse_args(["sub", "fizzl"])
    assert _cmd_path(args) == ["sub", "fizzle"]


def test_ambiguous_prefix_errors():
    msg = _error(_app(abbrev_commands=True), ["sub", "fi"])
    assert "ambiguous command 'fi' (could be 'fizz', 'fizzle')" in msg
    assert "__cli_cmd__" not in msg


def test_unknown_command_lists_choices():
    msg = _error(_app(abbrev_commands=True), ["sub", "zzz"])
    assert msg == (
        "Could not parse command line: unknown command 'zzz' "
        "(choose from 'buzz', 'fizz', 'fizzle')"
    )


def test_typo_suggests_close_match():
    msg = _error(_app(), ["sub", "buz"])
    assert "did you mean 'buzz'?" in msg


def test_child_can_disable_inherited_abbrev():
    app = _app(abbrev_commands=True, sub_meta={"abbrev_commands": False})
    assert _cmd_path(app.parse_args(["s", "buzz"])) == ["sub", "buzz"]
    msg = _error(app, ["sub", "bu"])
    assert "unknown command 'bu'" in msg


def test_child_can_enable_abbrev_locally():
    app = _app(sub_meta={"abbrev_commands": True})
    assert _cmd_path(app.parse_args(["sub", "bu"])) == ["sub", "buzz"]
    assert "unknown command 's'" in _error(app, ["s", "buzz"])


def test_abbreviated_command_dispatches():
    app = _app(abbrev_commands=True)
    assert app.dispatch(["s", "bu"]) == "buzz"


# Flags
# ========================


def test_options_abbreviated_by_default():
    args = _app().parse_args(["sub", "buzz", "--verb"])
    assert args.verbose is True


def test_options_abbrev_can_be_disabled():
    app = _app(abbrev_options=False)
    with pytest.raises(argparse.ArgumentError, match="--verb"):
        app.parse_args(["sub", "buzz", "--verb"])
    assert app.parse_args(["sub", "buzz", "--verbose"]).verbose is True


# Adapter level
# ========================


def test_subparsers_action_aliases_are_not_ambiguous():
    parser = ArgumentParser(prog="x", exit_on_error=False)
    subs = parser.add_subparsers(dest="cmd", action=SubParsersAction, allow_abbrev=True)
    subs.add_parser("remove", aliases=["rm"])
    subs.add_parser("rename")
    assert parser.parse_args(["rem"]).cmd == "remove"
    assert parser.parse_args(["rm"]).cmd == "rm"
    with pytest.raises(argparse.ArgumentError, match="ambiguous command 're'"):
        parser.parse_args(["re"])


def test_subparsers_action_abbrev_off_by_default():
    parser = ArgumentParser(prog="x", exit_on_error=False)
    subs = parser.add_subparsers(dest="cmd", action=SubParsersAction)
    subs.add_parser("remove")
    with pytest.raises(argparse.ArgumentError, match="unknown command 'rem'"):
        parser.parse_args(["rem"])
