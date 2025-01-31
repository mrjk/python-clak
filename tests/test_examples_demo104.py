"""
Test examples from demo104.
"""

import pytest
from common import replace_with_placeholders

import clak.exception as exception
from examples.demo104_nested_deep import AppMain


@pytest.fixture
def demo104_app():
    """Fixture that provides an instance of the Demo104 application."""
    return AppMain(proc_name="demo104-test")


TEST_PARAMETERS = [
    # Test command1 basic (success case)
    (["command1", "Alice"], "Run Command 1: Hello Alice", 0),
    # Test command1 with force flag
    (["command1", "--force", "Bob"], "Run Command 1: Hello Bob", 0),
    # Test command2 with required name (success case)
    (["command2", "John"], "Run command 2 World on: John in 'config.yaml' file", 0),
    # Test command2 with aliases
    (
        ["command2", "--alias", "johnny", "--alias", "j-man", "John"],
        "Map: j-man -> John",
        0,
    ),
    # Test command2 with config
    (
        ["--config", "custom.yml", "command2", "John"],
        "Run command 2 World on: John in 'custom.yml' file",
        0,
    ),
    # Test command1 with nested sub1 command
    (
        ["command1", "sub1", "sub1", "arg1", "arg2"],
        "Command called with args: ['arg1', 'arg2']",
        0,
    ),
    # Test command1 with nested sub2 and sub2a commands
    (
        ["command1", "sub2", "sub2", "sub2a", "arg1", "arg2"],
        "Command called with args: ['arg1', 'arg2']",
        0,
    ),
    # Test with no arguments (shows help)
    ([], "For example, we can decide to who usage instead of long help", 0),
    # Test with help flag (shows help)
    (["--help"], "Demo application with options and many nested subcommands", 0),
    # Test with invalid command
    (["invalid-command"], "Could not parse command line: __cli_cmd__1", 2),
    # Test command2 without required name
    (["command2"], "the following arguments are required: NAME", 2),
    # Test with debug flag
    (["--debug", "command1", "Charlie"], "Run Command 1: Hello Charlie", 0),
    # Test sub2b command (should raise NotImplementedError)
    (["command1", "sub2", "sub2", "sub2b"], "No 'cli_run' method found", 31),
]


@pytest.mark.tags("examples", "examples-unit")
@pytest.mark.parametrize("cli_args, expected_output, expected_exit", TEST_PARAMETERS)
def test_demo104_nested_cli(
    demo104_app, capsys, cli_args, expected_output, expected_exit
):
    """Test various CLI combinations for the nested commands example."""

    exit_code = 0
    try:
        demo104_app.dispatch(cli_args, exit=True)
    except SystemExit as e:
        exit_code = e.code
    except Exception as e:
        exit_code = -1

    captured = capsys.readouterr()
    output = captured.out + captured.err

    print(f"Call: {' '.join(cli_args)}")
    print(f"Output  : {exit_code} {output}")
    print(f"Expected: {expected_exit} {expected_output}")

    # Verify the output contains expected string
    assert (
        expected_output in output
    ), f"Expected '{expected_output}' in output, but got: {output}"

    # Verify the exit code
    assert (
        exit_code == expected_exit
    ), f"Expected exit code {expected_exit}, but got: {exit_code}"


@pytest.mark.tags("examples", "examples-regressions")
@pytest.mark.parametrize("cli_args, expected_output, expected_exit", TEST_PARAMETERS)
def test_demo104_nested_cli_regression(
    demo104_app, capsys, data_regression, cli_args, expected_output, expected_exit
):
    """Regression test that captures and compares output data against stored values."""

    # Run the command and capture results
    err = None
    try:
        demo104_app.dispatch(cli_args, exit=True)
    except SystemExit as e:
        err = e
    except Exception as e:
        err = e

    captured = capsys.readouterr()
    output = captured.out + captured.err
    output = replace_with_placeholders(output)

    # Prepare regression data structure
    test_data = {
        "cli_args": cli_args,
        "output": output,
        "err": str(err),
    }

    # Compare against stored data
    data_regression.check(test_data)
