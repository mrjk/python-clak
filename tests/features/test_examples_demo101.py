"""
Test examples from demo101.
"""

import os.path

import pytest
import sh
from common import replace_with_placeholders

# from clak.parser import ClakParseError, ClakNotImplementedError
from examples.demo101_basic_minimal import AppMain


@pytest.fixture
def demo101_app():
    """Fixture that provides an instance of the Demo101 application."""
    return AppMain(parse=False, proc_name="demo101-test")


@pytest.fixture
def demo101_file():
    """Fixture that provides an instance of the Demo101 application."""
    return "examples/demo101_basic_minimal.py"


TEST_PARAMETERS = [
    # Test with just name (success case)
    (["John"], "Store name 'John' in config file: config.yaml", 0),
    # Test with name and custom config (success case)
    (
        ["--config", "custom.yml", "Alice"],
        "Store name 'Alice' in config file: custom.yml",
        0,
    ),
    # Test with short config option (success case)
    (["-c", "test.conf", "Bob"], "Store name 'Bob' in config file: test.conf", 0),
    # Test with no arguments (error case - shows help)
    ([], "No name provided", 0),
    # Test with help flag (shows help)
    (["--help"], "Demo application with two arguments", 0),
    # Test with invalid option (error case)
    (["--invalid", "John"], "unrecognized arguments", 2),
    # Test with missing value for config
    (
        ["--config"],
        "Could not parse command line: --config/-c expected one argument",
        2,
    ),
    # Test with multiple names (error case)
    (["John", "Alice"], "unrecognized arguments", 2),
]


@pytest.mark.tags("examples", "examples-unit")
@pytest.mark.parametrize("cli_args, expected_output, expected_exit", TEST_PARAMETERS)
def test_demo101_basic_minimal_cli(
    demo101_app, capsys, cli_args, expected_output, expected_exit
):
    """Test various CLI combinations for the basic minimal example."""

    exit_code = 0
    try:
        demo101_app.dispatch(cli_args, exit=True)
    except SystemExit as e:
        exit_code = e.code
    except Exception as e:
        exit_code = -1

    captured = capsys.readouterr()
    output = captured.out + captured.err

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


@pytest.mark.parametrize("cli_args, expected_output, expected_exit", TEST_PARAMETERS)
def test_demo101_basic_minimal_cli_regression(
    demo101_app, capsys, data_regression, cli_args, expected_output, expected_exit
):
    """Regression test that captures and compares output data against stored values."""

    # Run the command and capture results
    err = None
    try:
        demo101_app.dispatch(cli_args, exit=True)
    except SystemExit as e:
        err = e
    except Exception as e:
        err = e

    captured = capsys.readouterr()
    output = captured.out + captured.err

    # Prepare regression data structure
    test_data = {
        "cli_args": cli_args,
        "output": output,
        "err": str(err),
    }

    # Compare against stored data
    data_regression.check(test_data)


@pytest.mark.tags("examples", "examples-regressions-cli")
@pytest.mark.parametrize("cli_args, expected_output, expected_exit", TEST_PARAMETERS)
def test_demo101_basic_minimal_script_regression(
    capsys, data_regression, cli_args, demo101_file, expected_output, expected_exit
):
    """Regression test that executes the actual script file using sh library."""

    # Get the path to the demo script
    demo_script = sh.Command(demo101_file)
    output = "<???>"
    exit_code = 0

    try:
        output = demo_script(*cli_args, _err_to_out=True, _tty_out=True)
    except sh.ErrorReturnCode as e:
        output = str(e)
        exit_code = int(e.exit_code)

    output = replace_with_placeholders(output)
    assert expected_exit == exit_code

    # Prepare regression data structure
    test_data = {
        "cli_args": cli_args,
        "output": output,
        # "error": error,
        "exit_code": exit_code,
    }

    # Compare against stored data
    data_regression.check(test_data)
