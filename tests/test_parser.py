"""Unit tests for the clak.parser module.

This module contains test cases for the parser functionality including:
- Basic argument parsing
- Subcommand handling
- Help text generation
- Exception handling
- Command execution flow
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
import argparse

from clak.parser import (
    ParserNode,
    Argument,
    SubParser,
    Command,
    prepare_docstring,
    first_doc_line,
    FormatEnv,
)
from clak.exception import ClakParseError, ClakUserError, ClakError


# Basic Parser Tests
def test_parser_initialization():
    """Test basic parser initialization."""
    parser = ParserNode()
    parser.name = "test"  # Set name after initialization
    assert parser.name == "test"
    assert parser.key is None
    assert parser.children == {}
    assert isinstance(parser.registry, dict)


def test_parser_with_arguments():
    """Test parser with basic arguments."""
    parser = ParserNode()
    # Create a fresh parser without default arguments
    parser.parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    parser.arguments_dict = {
        "name": Argument("--name", help="Name argument"),
        "age": Argument("--age", type=int, help="Age argument"),
    }
    parser.init_options()
    
    args = parser.parse_args(["--name", "John", "--age", "25"])
    assert args.name == "John"
    assert args.age == 25


def test_argument_destination():
    """Test argument destination handling."""
    arg = Argument("--test-name", help="Test argument")
    assert arg._get_best_dest() == "test_name"

    arg = Argument("-t", "--test", help="Test argument")
    assert arg._get_best_dest() == "test"


@patch('sys.argv', ['prog', '--help'])
def test_help_display(capsys):
    """Test help text display."""
    parser = ParserNode()
    with pytest.raises(SystemExit):
        parser.parse_args()
    captured = capsys.readouterr()
    assert "usage:" in captured.out


# Subcommand Tests
# def test_basic_subcommand():
#     """Test basic subcommand structure."""
    
#     def run_cmd(self, ctx, **kwargs):
#         return "subcmd_executed"

#     sub_parser = ParserNode()
#     sub_parser.cli_run = run_cmd

#     main_parser = ParserNode()
#     # Create fresh parser without default arguments
#     main_parser.parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
#     main_parser.children = {"sub": Command(sub_parser.__class__, sub_parser)}
#     main_parser.init_subcommands()
#     main_parser.__dict__["cli_run"] = run_cmd

#     try:
#         result = main_parser.dispatch([])
#         # result = main_parser.dispatch(['sub'])
#         assert result == "subcmd_executed"
#     except SystemExit as e:
#         pytest.fail(f"SystemExit was raised with code {e.code}")


# def test_nested_subcommands():
#     """Test nested subcommand structure."""
#     def leaf_run(ctx, **kwargs):
#         return "leaf_executed"

#     leaf_parser = ParserNode()
#     leaf_parser.cli_run = leaf_run

#     mid_parser = ParserNode()
#     mid_parser.children = {"leaf": Command(leaf_parser.__class__, leaf_parser)}

#     root_parser = ParserNode()
#     # Create fresh parser without default arguments
#     root_parser.parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
#     root_parser.children = {"mid": Command(mid_parser.__class__, mid_parser)}
#     root_parser.init_subcommands()

#     try:
#         with patch('sys.argv', ['prog', 'mid', 'leaf']):
#             result = root_parser.dispatch()
#             assert result == "leaf_executed"
#     except SystemExit as e:
#         pytest.fail(f"SystemExit was raised with code {e.code}")


# # Exception Handling Tests
# def test_parse_error():
#     """Test handling of parse errors."""
#     parser = ParserNode()
#     # Create fresh parser without default arguments
#     parser.parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
#     parser.arguments_dict = {
#         "age": Argument("--age", type=int, required=True)
#     }
#     parser.init_options()

#     with pytest.raises((ClakParseError, argparse.ArgumentError)):
#         parser.parse_args([])


def test_user_error():
    """Test handling of user errors."""
    def run_cmd(**kwargs):
        raise ClakUserError("User error")

    parser = ParserNode()
    parser.cli_run = run_cmd

    with pytest.raises(SystemExit):
        parser.dispatch([])


# Utility Function Tests
def test_first_doc_line():
    """Test first_doc_line function."""
    doc = """First line
    Second line
    Third line"""
    assert first_doc_line(doc) == "First line"


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


# Command Execution Tests
# def test_cli_group_execution():
#     """Test cli_group method execution."""
#     mock_group = MagicMock()

#     parser = ParserNode()
#     # Create fresh parser without default arguments
#     parser.parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
#     parser.cli_group = mock_group

#     try:
#         parser.dispatch([])
#         assert mock_group.called
#     except SystemExit as e:
#         pytest.fail(f"SystemExit was raised with code {e.code}")


# def test_cli_run_execution():
#     """Test cli_run method execution."""
#     mock_run = MagicMock()

#     parser = ParserNode()
#     # Create fresh parser without default arguments
#     parser.parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
#     parser.cli_run = mock_run

#     try:
#         parser.dispatch([])
#         assert mock_run.called
#     except SystemExit as e:
#         pytest.fail(f"SystemExit was raised with code {e.code}")

