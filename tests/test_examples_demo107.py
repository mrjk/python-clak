"""
Test examples from demo107 (docstring customization).
"""

import pytest
from common import replace_with_placeholders

import clak.exception as exception
from examples.demo107_docstring_meta import AppMain


@pytest.fixture
def demo107_app():
    """Fixture that provides an instance of the Demo107 application."""
    return AppMain(parse=False, proc_name="demo107-test")


TEST_PARAMETERS = [
    # Test command1 basic (success case)
    (["command1"], "Source: Water from the mountains", 0),
    # Test command1 with source option
    (["command1", "--source", "Lake"], "Source: Lake", 0),
    # Test command1 with force flag
    (["command1", "--force", "--source", "River"], "Source: River", 0),
    # Test command2 with required name (success case)
    (["command2", "John"], "Run Command 2: World", 0),
    # Test command2 with all options including inherited ones
    (
        ["command2", "--source", "Lake", "--force", "--destination", "/tmp", "John"],
        "Dump 'John' in: /tmp",
        0,
    ),
    # Test help on main app to verify custom description and epilog
    (["--help"], "Hello World of CLI !", 0),
    # Test help on main app to verify epilog
    (["--help"], "And this is a very short documentation epilog", 0),
    # Test help on command1 to verify custom epilog
    (["command1", "--help"], "Another epilog for this child command", 0),
    # Test help on command2 to verify custom usage
    (["command2", "--help"], "command usage for command2 can be overriden", 0),
    # Test with no arguments (shows help with custom description)
    ([], "Hello World of CLI !", 0),
    # Test with invalid command
    (["invalid-command"], "Could not parse command line: __cli_cmd__1", 2),
    # Test command2 without required name
    (["command2"], "the following arguments are required: name", 2),
    # Test with debug flag
    (["--debug", "command1"], "Source: Water from the mountains", 0),
]


@pytest.mark.tags("examples", "examples-unit")
@pytest.mark.parametrize("cli_args, expected_output, expected_exit", TEST_PARAMETERS)
def test_demo107_docstring_cli(
    demo107_app, capsys, cli_args, expected_output, expected_exit
):
    """Test various CLI combinations for the docstring customization example."""

    exit_code = 0
    try:
        demo107_app.dispatch(cli_args, exit=True)
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
def test_demo107_docstring_cli_regression(
    demo107_app, capsys, data_regression, cli_args, expected_output, expected_exit
):
    """Regression test that captures and compares output data against stored values."""

    # Run the command and capture results
    err = None
    try:
        demo107_app.dispatch(cli_args, exit=True)
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
