"""Tests for Meta.parse_intermixed (Unix-style flag/positional mix on leaves)."""

# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods

import argparse

import pytest

from clak import Arg, Argument, Command, Opt, Parser

pytestmark = pytest.mark.tags("unit-tests")


def _grep_leaf():
    class Grep(Parser):
        pattern = Arg("pattern")
        files = Arg("files", nargs="*")
        ignore_case = Opt("-i", "--ignore-case", action="store_true")

        def cli_run(self, **_):
            return None

    return Grep


def test_intermixed_default_collects_positionals_after_flag():
    """Default on: later positionals join nargs=* after a flag.

    Must not RecursionError on Python 3.10–3.11, where stdlib intermixed
    parse calls parse_known_args internally.
    """

    class App(_grep_leaf()):
        pass

    app = App(parse=False, add_help=False)
    args = app.parse_args(["foo", "a.txt", "-i", "b.txt"])
    assert args.pattern == "foo"
    assert args.ignore_case is True
    assert args.files == ["a.txt", "b.txt"]


def test_intermixed_opt_out_rejects_positionals_after_flag():
    """Meta.parse_intermixed = False restores argparse leftover errors."""

    class App(_grep_leaf()):
        class Meta:
            parse_intermixed = False

    app = App(parse=False, add_help=False)
    with pytest.raises(argparse.ArgumentError, match="unrecognized arguments"):
        app.parse_args(["foo", "a.txt", "-i", "b.txt"])


def test_intermixed_nested_inherits_and_skips_parent_subparsers():
    """Default applies to the leaf; parent flags still work before the command."""

    class Grep(_grep_leaf()):
        pass

    class App(Parser):
        debug = Argument("--debug", action="store_true")
        grep = Command(Grep, help="Search files")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=False)
    args = app.parse_args(["--debug", "grep", "foo", "a.txt", "-i", "b.txt"])
    assert args.debug is True
    assert args.pattern == "foo"
    assert args.ignore_case is True
    assert args.files == ["a.txt", "b.txt"]


def test_intermixed_child_opt_out():
    """Child Meta.parse_intermixed = False wins over the default True parent."""

    class Grep(_grep_leaf()):
        class Meta:
            parse_intermixed = False

    class App(Parser):
        grep = Command(Grep, help="Search files")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=False)
    with pytest.raises(argparse.ArgumentError, match="unrecognized arguments"):
        app.parse_args(["grep", "foo", "a.txt", "-i", "b.txt"])


def test_intermixed_remainder_falls_back_without_typeerror():
    """nargs remainder is incompatible; keep standard parse (no TypeError)."""

    class App(Parser):
        cmd = Arg("cmd")
        rest = Arg("rest", nargs="...")
        extra = Opt("--extra")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=False)
    args = app.parse_args(["doit", "1", "--extra", "bar"])
    assert args.cmd == "doit"
    assert args.rest == ["1", "--extra", "bar"]
    assert args.extra is None
