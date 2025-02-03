"""
Test examples from demo102.
"""

import os.path

import pytest
import sh
from common import replace_with_placeholders

import tests.features.demo_features.demo102_basic_argparse as example
from tests.common import replace_with_placeholders


@pytest.fixture
def demo102_app():
    """Fixture that provides an instance of the Demo102 application."""
    return example.AppMain(parse=False, proc_name="demo102-test")


@pytest.fixture
def demo102_file():
    """Fixture that provides the path to the Demo102 script file."""
    return example.__file__


TEST_PARAMETERS = [
    # Test with required arguments (success case)
    (["John", "Smith"], "Identity: John Smith", 0),
    # Test with all optional arguments
    (
        [
            "--force",
            "--config",
            "custom.yml",
            "--color",
            "red",
            "--items",
            "item1",
            "--items",
            "item2",
            "John",
            "Smith",
            "alias1",
            "alias2",
        ],
        "Force mode update config file: custom.yml",
        0,
    ),
    # Test with default surname
    (["John"], "Identity: John Doe", 0),
    # Test with no arguments (error case - shows help)
    ([], "the following arguments are required: NAME", 2),
    # Test with help flag (shows help)
    (["--help"], "Demo application with many arguments", 0),
    # Test with invalid color choice
    (
        ["--color", "yellow", "John"],
        "Could not parse command line: --color/-r invalid choice: 'yellow'",
        2,
    ),
    # Test with missing value for config
    (
        ["--config", "new_conf.yml"],
        "error: the following arguments are required: NAME",
        2,
    ),
    # Test with items list
    (["--items", "book", "--items", "pen", "John"], "Item: book", 0),
]


@pytest.mark.tags("examples", "examples-unit")
@pytest.mark.parametrize("cli_args, expected_output, expected_exit", TEST_PARAMETERS)
def test_demo102_basic_argparse_cli(
    demo102_app, capsys, cli_args, expected_output, expected_exit
):
    """Test various CLI combinations for the basic argparse example."""

    exit_code = 0
    try:
        demo102_app.dispatch(cli_args, exit=True)
    except SystemExit as e:
        exit_code = e.code
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
def test_demo102_basic_argparse_cli_regression(
    demo102_app, capsys, data_regression, cli_args, expected_output, expected_exit
):
    """Regression test that captures and compares output data against stored values."""

    # Run the command and capture results
    err = None
    try:
        demo102_app.dispatch(cli_args, exit=True)
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
def test_demo102_basic_minimal_script_regression(
    capsys, data_regression, cli_args, demo102_file, expected_output, expected_exit
):
    """Regression test that executes the actual script file using sh library."""

    # Get the path to the demo script
    demo_script = sh.Command(demo102_file)

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
