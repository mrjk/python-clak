"""
Test examples from demo105 (inheritance of common options).
"""

import os.path

import pytest
import sh
from common import replace_with_placeholders

import tests.features.demo_features.demo105_inherit as example
from tests.common import replace_with_placeholders


@pytest.fixture
def demo105_app():
    """Fixture that provides an instance of the Demo105 application."""
    return example.AppMain(parse=False, proc_name="demo105-test")


@pytest.fixture
def demo105_file():
    """Fixture that provides the path to the Demo105 script file."""
    return example.__file__


TEST_PARAMETERS = [
    # Test command1 basic (success case)
    (["command1"], "Source: Water from the mountains", 0),
    # Test command1 with source option
    (["command1", "--source", "Lake"], "Source: Lake", 0),
    # Test command1 with force flag
    (["command1", "--force", "--source", "River"], "Source: River", 0),
    # Test command2 with required name (success case)
    (["command2", "John"], "Run Command 2: World", 0),
    # Test command2 with all options
    (
        ["command2", "--source", "Lake", "--destination", "/tmp", "John"],
        "Dump 'John' in: /tmp",
        0,
    ),
    # Test command2 with force and source inherited from CommonOptions
    (
        ["command2", "--force", "--source", "River", "--destination", "/tmp", "John"],
        "Dump 'John' in: /tmp",
        0,
    ),
    # Test with no arguments (shows help)
    ([], "Demo application with options and two subcommands", 0),
    # Test with help flag (shows help)
    (["--help"], "Demo application with options and two subcommands", 0),
    # Test with invalid command
    (["invalid-command"], "Could not parse command line: __cli_cmd__1", 2),
    # Test command2 without required name
    (["command2"], "the following arguments are required: name", 2),
    # Test with debug flag
    (["--debug", "command1"], "Source: Water from the mountains", 0),
    # Test with config option
    (["--config", "custom.yml", "command1"], "Source: Water from the mountains", 0),
]


@pytest.mark.tags("examples", "examples-unit")
@pytest.mark.parametrize("cli_args, expected_output, expected_exit", TEST_PARAMETERS)
def test_demo105_inherit_cli(
    demo105_app, capsys, cli_args, expected_output, expected_exit
):
    """Test various CLI combinations for the inheritance example."""

    exit_code = 0
    try:
        demo105_app.dispatch(cli_args, exit=True)
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


@pytest.mark.tags("examples", "examples-regressions")
@pytest.mark.parametrize("cli_args, expected_output, expected_exit", TEST_PARAMETERS)
def test_demo105_inherit_cli_regression(
    demo105_app, capsys, data_regression, cli_args, expected_output, expected_exit
):
    """Regression test that captures and compares output data against stored values."""

    # Run the command and capture results
    err = None
    try:
        demo105_app.dispatch(cli_args, exit=True)
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


@pytest.mark.tags("examples", "examples-regressions-cli")
@pytest.mark.parametrize("cli_args, expected_output, expected_exit", TEST_PARAMETERS)
def test_demo105_basic_minimal_script_regression(
    capsys, data_regression, cli_args, demo105_file, expected_output, expected_exit
):
    """Regression test that executes the actual script file using sh library."""

    # Get the path to the demo script
    demo_script = sh.Command(demo105_file)

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
        "exit_code": exit_code,
    }

    # Compare against stored data
    data_regression.check(test_data)
