"""Unit tests for the clak.parser module.

This module contains test cases for the parser functionality including:
- Basic argument parsing
- Subcommand handling
- Help text generation
- Exception handling
- Command execution flow
"""

import argparse
import logging
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from clak.descriptors import FormatEnv, first_doc_line, prepare_docstring
from clak.exception import ClakError, ClakParseError, ClakUserError
from clak.parser import (
    Arg,
    Argument,
    Command,
    Opt,
    Parser,
    ParserNode,
    SubParser,
)

pytestmark = pytest.mark.tags("unit-tests")


# Basic Parser Tests
def test_parser_initialization():
    """Test basic parser initialization."""
    parser = ParserNode()
    parser.name = "test"  # Set name after initialization
    assert parser.name == "test"
    assert parser.key is None
    assert parser.meta__subcommands_dict == {}
    assert isinstance(parser.registry, dict)


def test_parser_with_arguments():
    """Test parser with basic arguments."""
    parser = ParserNode()
    # Create a fresh parser without default arguments
    parser.parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    parser.meta__arguments_dict = {
        "name": Argument("--name", help="Name argument"),
        "age": Argument("--age", type=int, help="Age argument"),
    }
    parser.add_arguments()

    args = parser.parse_args(["--name", "John", "--age", "25"])
    assert args.name == "John"
    assert args.age == 25


def test_argument_destination():
    """Test argument destination handling."""
    arg = Argument("--test-name", help="Test argument")
    assert arg._get_best_dest() == "test_name"

    arg = Argument("-t", "--test", help="Test argument")
    assert arg._get_best_dest() == "test"


def test_arg_opt_public_import():
    """Arg and Opt are optional helpers exported from clak."""
    from clak import Arg as TopArg
    from clak import Opt as TopOpt

    assert TopArg is Arg
    assert TopOpt is Opt
    assert issubclass(Arg, Argument)
    assert issubclass(Opt, Argument)
    assert isinstance(Arg("NAME"), Argument)
    assert isinstance(Opt("--verbose"), Argument)


def test_arg_opt_parse_happy_path():
    """Parser accepts Opt flags and Arg positionals like Argument."""

    class App(Parser):
        verbose = Opt("-v", "--verbose", action="store_true", help="Verbose")
        name = Arg("NAME", help="Who to greet")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=False)
    args = app.parse_args(["-v", "Ada"])
    assert args.verbose is True
    assert args.name == "Ada"

    args = app.parse_args(["Ada"])
    assert args.verbose is False
    assert args.name == "Ada"


def test_arg_rejects_option_flags():
    """Arg must not be given option flags."""
    with pytest.raises(ValueError, match="option flag '--miss-placed-option'"):
        Arg("--miss-placed-option")
    with pytest.raises(ValueError, match="option flag '--flag'"):
        Arg("NAME", "--flag")
    with pytest.raises(ValueError, match="option flag '-v'"):
        Arg("-v")


def test_opt_rejects_positionals():
    """Opt must not be given positional names."""
    with pytest.raises(ValueError, match="positional 'miss_placed_arg'"):
        Opt("miss_placed_arg")
    with pytest.raises(ValueError, match="positional 'NAME'"):
        Opt("-v", "NAME")


def test_opt_dest_derived_flag_allowed():
    """Opt with no names still uses dest-derived flags."""
    opt = Opt(action="store_true", help="Verbose")
    assert opt.args == ()


def test_arg_empty_names_rejected():
    """Arg() with no positional name must not become a dest-derived flag."""
    with pytest.raises(ValueError, match="requires a positional name"):
        Arg()
    with pytest.raises(ValueError, match="requires a positional name"):
        Arg(help="Who to greet")


def test_option_group_reuses_same_title():
    """Same option_group title reuses one argparse argument group."""

    class App(Parser):
        a = Argument("--alpha", option_group="Custom", help="A")
        b = Argument("--beta", option_group="Custom", help="B")
        c = Argument("--gamma", help="C")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=True)
    groups = getattr(app.parser, "_clak_argument_groups", {})
    assert list(groups) == ["Custom"]
    help_text = app.parser.format_help()
    assert help_text.count("Custom:") == 1
    assert "--alpha" in help_text
    assert "--beta" in help_text
    assert "--gamma" in help_text
    custom_idx = help_text.index("Custom:")
    assert help_text.index("--alpha", custom_idx) > custom_idx
    assert help_text.index("--beta", custom_idx) > custom_idx


def test_argument_group_and_option_group_share_title_cache():
    """argument_group and option_group with the same title reuse one section."""

    class App(Parser):
        path = Argument("path", argument_group="Shared", help="Path")
        flag = Argument("--flag", option_group="Shared", help="Flag")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=True)
    groups = getattr(app.parser, "_clak_argument_groups", {})
    assert list(groups) == ["Shared"]
    assert app.parser.format_help().count("Shared:") == 1


def test_argument_group_and_option_group_both_set_raises():
    """Setting both help-group kwargs on one Argument is an error."""

    class App(Parser):
        bad = Argument(
            "--bad",
            argument_group="A",
            option_group="B",
            help="Nope",
        )

        def cli_run(self, **_):
            return None

    with pytest.raises(
        ValueError, match="cannot set both argument_group and option_group"
    ):
        App(parse=False, add_help=True)


def test_option_group_kwarg_not_passed_to_argparse():
    """option_group= is Clak-only and must not reach add_argument."""

    class App(Parser):
        output_format = Argument(
            "--format", option_group="Output options", help="Format"
        )

        def cli_run(self, **_):
            return None

    # Would raise TypeError if option_group leaked into argparse.add_argument
    app = App(parse=False, add_help=True)
    assert "Output options:" in app.parser.format_help()
    args = app.parse_args(["--format", "x"])
    assert args.output_format == "x"


def test_exclusive_group_rejects_both_flags():
    """Same exclusive_group key enforces argparse mutual exclusion."""

    class App(Parser):
        json = Argument("--json", action="store_true", exclusive_group="format")
        yaml = Argument("--yaml", action="store_true", exclusive_group="format")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=True)
    args = app.parse_args(["--json"])
    assert args.json is True
    assert args.yaml is False

    with pytest.raises(argparse.ArgumentError, match="not allowed with argument"):
        app.parse_args(["--json", "--yaml"])


def test_exclusive_group_kwarg_not_passed_to_argparse():
    """exclusive_group= is Clak-only and must not reach add_argument."""

    class App(Parser):
        quiet = Argument("--quiet", action="store_true", exclusive_group="v")
        verbose = Argument("--verbose", action="store_true", exclusive_group="v")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=True)
    args = app.parse_args(["--quiet"])
    assert args.quiet is True


def test_exclusive_group_nests_under_option_group():
    """exclusive_group under option_group still appears in the help section."""

    class App(Parser):
        quiet = Argument(
            "--quiet",
            action="store_true",
            option_group="Output options",
            exclusive_group="verbosity",
        )
        verbose = Argument(
            "--verbose",
            action="store_true",
            option_group="Output options",
            exclusive_group="verbosity",
        )

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=True)
    groups = getattr(app.parser, "_clak_argument_groups", {})
    assert list(groups) == ["Output options"]
    help_text = app.parser.format_help()
    assert "Output options:" in help_text
    output_idx = help_text.index("Output options:")
    assert help_text.index("--quiet", output_idx) > output_idx
    assert help_text.index("--verbose", output_idx) > output_idx

    with pytest.raises(argparse.ArgumentError, match="not allowed with argument"):
        app.parse_args(["--quiet", "--verbose"])


def test_command_group_kwarg_not_passed_to_argparse():
    """command_group= is Clak-only and must not reach add_parser."""

    class Child(Parser):
        def cli_run(self, **_):
            return None

    class App(Parser):
        child = Command(Child, command_group="base", help="A child")

        def cli_run(self, **_):
            return None

    app = App(parse=False, add_help=True)
    assert "child" in app.parser.format_help()
    app.parse_args(["child"])
    # pylint: disable=protected-access
    choice = app.subparsers._choices_actions[-1]
    assert choice._clak_command_group == "base"


@patch("sys.argv", ["prog", "--help"])
def test_help_display(capsys):
    """Test help text display."""
    parser = ParserNode()
    with pytest.raises(SystemExit):
        parser.parse_args()
    captured = capsys.readouterr()
    assert "usage:" in captured.out


# Subcommand Tests
def test_basic_subcommand():
    """Test basic subcommand structure."""

    def run_cmd(ctx, **kwargs):
        print("subcmd_executed")
        return "subcmd_executed"

    sub_parser = ParserNode()
    sub_parser.cli_run = run_cmd

    main_parser = ParserNode()
    # Create fresh parser without default arguments
    main_parser.parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    main_parser.meta__subcommands_dict = {
        "sub": Command(sub_parser.__class__, sub_parser)
    }
    main_parser.add_subcommands()
    # main_parser.__dict__["cli_run"] = run_cmd
    setattr(main_parser, "cli_run", run_cmd)

    try:
        result = main_parser.dispatch([])
        # result = main_parser.dispatch(['sub'])
        assert result == "subcmd_executed"
    except SystemExit as e:
        pytest.fail(f"SystemExit was raised with code {e.code}")


def test_child_command_attr_overrides_parent():
    """Subclass Command attr wins over the parent (same as Argument MRO)."""

    class LeafA(Parser):
        def cli_run(self, **_):
            return "A"

    class LeafB(Parser):
        def cli_run(self, **_):
            return "B"

    class Parent(Parser):
        sub = Command(LeafA, help="parent")

        def cli_run(self, **_):
            return None

    class Child(Parent):
        sub = Command(LeafB, help="child")

    app = Child(parse=False, add_help=False)
    assert app.children["sub"].__class__ is LeafB
    assert app.dispatch(["sub"]) == "B"


def test_help_long_subcommand_name_wraps():
    """Long subcommand names put help on the next line instead of smashing."""

    class Leaf(Parser):
        "Does a useful thing."

        def cli_run(self, **_):
            return None

    class App(Parser):
        "Root."

        very_long_subcommand_name_that_overflows_help = Command(
            Leaf, help="does a useful thing"
        )

    help_text = App(parse=False, add_help=True).parser.format_help()
    name = "very_long_subcommand_name_that_overflows_help"
    assert name in help_text
    assert "does a useful thing" in help_text
    for line in help_text.splitlines():
        if name in line:
            assert "does a useful thing" not in line


def test_user_error():
    """Test handling of user errors."""

    def run_cmd(**kwargs):
        raise ClakUserError("User error")

    parser = ParserNode()
    parser.cli_run = run_cmd

    with pytest.raises(SystemExit):
        parser.dispatch([])


class _DemoAppError(Exception):
    rc = 44


def test_known_exception_uses_rc(capsys):
    """Known app exceptions exit with err.rc (Paasify-style)."""

    def run_cmd(**_):
        raise _DemoAppError("application missing")

    parser = ParserNode()
    parser.meta__known_exceptions = [_DemoAppError]
    parser.cli_run = run_cmd

    with pytest.raises(SystemExit) as exc:
        parser.dispatch([])
    assert exc.value.code == 44
    assert "application missing" in capsys.readouterr().err


def test_exception_handlers_third_party(capsys):
    """Meta.exception_handlers map library errors to clean messages."""

    class _LibError(Exception):
        pass

    def handle_lib(_app, err):
        print(f"handled: {err}")
        sys.exit(42)

    def run_cmd(**_):
        raise _LibError("bad config")

    parser = ParserNode()
    parser.meta__exception_handlers = [(_LibError, handle_lib)]
    parser.cli_run = run_cmd

    with pytest.raises(SystemExit) as exc:
        parser.dispatch([])
    assert exc.value.code == 42
    assert "handled: bad config" in capsys.readouterr().out


def test_exception_handler_return_code_honored(capsys):
    """Handler int return becomes the process exit code."""

    class _AppError(Exception):
        rc = 1

    def handle_app(_app, err):
        print(f"caught: {err}", file=sys.stderr)
        return 42

    def run_cmd(**_):
        raise _AppError("boom")

    parser = ParserNode()
    parser.meta__known_exceptions = [(_AppError, handle_app)]
    parser.cli_run = run_cmd

    with pytest.raises(SystemExit) as exc:
        parser.dispatch([])
    assert exc.value.code == 42
    assert "caught: boom" in capsys.readouterr().err


def test_os_error_exit_uses_errno_or_one(monkeypatch):
    """OSError subclasses exit with errno, falling back to 1 when unset."""

    parser = ParserNode()
    monkeypatch.setattr("clak.core.parser.logger.critical", lambda *a, **k: None)

    with pytest.raises(SystemExit) as exc:
        parser.clean_terminate(FileNotFoundError(2, "missing"))
    assert exc.value.code == 2

    err = OSError("synthetic")
    err.errno = None
    with pytest.raises(SystemExit) as exc:
        parser.clean_terminate(err)
    assert exc.value.code == 1


def test_parse_args_string_uses_shlex():
    """Quoted tokens in a string argv are preserved."""

    class App(ParserNode):
        path = Argument("path")

        def cli_run(self, **_):
            return None

    app = App()
    ns = app.parse_args('"/tmp/my file.txt"')
    assert ns.path == "/tmp/my file.txt"


def test_uncaught_error_reports_bug(monkeypatch):
    """Unhandled exceptions get the developer bug message."""

    def run_cmd(**_):
        raise RuntimeError("boom")

    messages = []

    def _critical(msg, *args, **_kwargs):
        messages.append(msg % args if args else str(msg))

    monkeypatch.setattr("clak.core.parser.logger.critical", _critical)
    monkeypatch.setattr("clak.core.parser.logger.error", lambda *a, **k: None)

    parser = ParserNode()
    parser.cli_run = run_cmd

    with pytest.raises(SystemExit) as exc:
        parser.dispatch([])
    assert exc.value.code == 1
    text = "\n".join(messages)
    assert "may be a bug" in text
    assert "report to the developer" in text


def test_clean_terminate_broken_pipe(caplog, monkeypatch):
    """BrokenPipeError exits quietly with code 1 (no bug / OS-error log)."""

    def fake_exit_broken_pipe(rc=1):
        raise SystemExit(rc)

    monkeypatch.setattr("clak.core.parser._exit_broken_pipe", fake_exit_broken_pipe)

    parser = ParserNode()
    with caplog.at_level(logging.CRITICAL):
        with pytest.raises(SystemExit) as exc:
            parser.clean_terminate(BrokenPipeError(32, "Broken pipe"))
    assert exc.value.code == 1
    assert "may be a bug" not in caplog.text
    assert "Uncaught error" not in caplog.text
    assert "Program exited with OS error" not in caplog.text


def test_broken_pipe_during_view_render(caplog, monkeypatch):
    """Pipe break during view print goes through clean_terminate, not bug path."""
    from clak.views import ListView

    def fake_exit_broken_pipe(rc=1):
        raise SystemExit(rc)

    monkeypatch.setattr("clak.core.parser._exit_broken_pipe", fake_exit_broken_pipe)

    def run_cmd(**_):
        return ListView([{"name": "a"}, {"name": "b"}])

    def boom_print(*_args, **_kwargs):
        raise BrokenPipeError(32, "Broken pipe")

    monkeypatch.setattr("builtins.print", boom_print)

    parser = ParserNode()
    parser.cli_run = run_cmd

    with caplog.at_level(logging.CRITICAL):
        with pytest.raises(SystemExit) as exc:
            parser.dispatch([])
    assert exc.value.code == 1
    assert "may be a bug" not in caplog.text
    assert "report to the developer" not in caplog.text


# Utility Function Tests
def test_first_doc_line():
    """Test first_doc_line function."""
    doc = """First line
    Second line
    Third line"""
    assert first_doc_line(doc) == "First line"
    assert first_doc_line(None) == ""
    assert first_doc_line("") == ""


def test_prepare_docstring():
    """Test prepare_docstring function."""
    doc = """Test {name}
    With {value}"""
    vars = {"name": "test", "value": 123}
    result = prepare_docstring(doc, variables=vars)
    assert "Test test" in result
    assert "With 123" in result


def test_format_env():
    """Test FormatEnv class."""
    env = FormatEnv({"test": "value"})
    vars = env.get()
    assert vars["test"] == "value"
    assert "type" in vars  # Check default values


def _nested_parse_error_app():
    """Root -> group -> leaf, plus a sibling command with a required NAME."""

    class Leaf(Parser):
        foo = Argument("--foo", help="Leaf option")

        def cli_run(self, **_):
            return None

    class Group(Parser):
        leaf = Command(Leaf, help="Leaf command")

        def cli_run(self, **_):
            return None

    class Command2(Parser):
        name = Argument("NAME", help="Name")

        def cli_run(self, **_):
            return None

    class App(Parser):
        group = Command(Group, help="Group command")
        command2 = Command(Command2, help="Needs NAME")

        def cli_run(self, **_):
            return None

    return App(parse=False, proc_name="app")


def _dispatch_output(app, cli_args, capsys):
    with pytest.raises(SystemExit) as exc:
        app.dispatch(cli_args)
    captured = capsys.readouterr()
    return exc.value.code, captured.out + captured.err


def test_nested_unknown_flag_prints_leaf_usage(capsys):
    """Leftover tokens on a nested command print that leaf usage, not root."""
    app = _nested_parse_error_app()
    rc, output = _dispatch_output(app, ["group", "leaf", "--nope"], capsys)
    assert rc == 2
    assert "usage:" in output
    assert "group leaf" in output
    assert "{group" not in output
    assert "unrecognized arguments: --nope" in output


def test_nested_missing_positional_prints_leaf_usage(capsys):
    """Missing required arg on a nested command prints that command usage."""
    app = _nested_parse_error_app()
    rc, output = _dispatch_output(app, ["command2"], capsys)
    assert rc == 2
    assert "usage:" in output
    assert "command2" in output
    assert "{group" not in output
    assert "the following arguments are required: NAME" in output


def test_invalid_top_level_command_prints_root_usage(capsys):
    """Unknown top-level command still prints root usage with the command set."""
    app = _nested_parse_error_app()
    rc, output = _dispatch_output(app, ["nope"], capsys)
    assert rc == 2
    assert "usage:" in output
    assert "{group" in output
    assert "invalid choice" in output


def test_one_level_unknown_flag_prints_root_usage(capsys):
    """A one-level CLI unknown flag still prints that parser's usage."""

    class App(Parser):
        foo = Argument("--foo", help="An option")

        def cli_run(self, **_):
            return None

    app = App(parse=False, proc_name="app")
    rc, output = _dispatch_output(app, ["--nope"], capsys)
    assert rc == 2
    assert "usage:" in output
    assert "usage: app" in output
    assert "unrecognized arguments: --nope" in output
