"""
Test examples from demo108 (exception handling).
"""

import os.path

import pytest
import sh
from common import replace_with_placeholders

import tests.features.demo_features.demo108_exceptions as example
from tests.common import replace_with_placeholders


@pytest.fixture
def demo108_app():
    """Fixture that provides an instance of the Demo108 application."""
    return example.AppMain(parse=False, proc_name="demo108-test")


@pytest.fixture
def demo108_file():
    """Fixture that provides the path to the Demo108 script file."""
    return example.__file__


TEST_PARAMETERS = [
    # Test showing help with no arguments
    ([], "Demo application with exception handlers", 0),
    # Test command1 raises ClakNotImplementedError
    (["command1"], "No 'cli_run' method found for", 31),
    # Test command2 raises AppException with custom handler
    (["command2"], "Manipulated error: Custom exception", 1),
    # TODO: Exception error message is too different from the one in the script
    # Test command3 raises uncaught RuntimeError
    # (["command3"], "", 1),
]


@pytest.mark.tags("examples", "examples-unit")
@pytest.mark.parametrize("cli_args, expected_output, expected_exit", TEST_PARAMETERS)
def test_demo108_exceptions_cli(
    demo108_app, capsys, cli_args, expected_output, expected_exit
):
    """Test various CLI combinations for the exception handling example."""

    exit_code = 0
    try:
        demo108_app.dispatch(cli_args, exit=True)
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
def test_demo108_exceptions_cli_regression(
    demo108_app, capsys, data_regression, cli_args, expected_output, expected_exit
):
    """Regression test that captures and compares output data against stored values."""

    # Run the command and capture results
    err = None
    try:
        demo108_app.dispatch(cli_args, exit=True)
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
def test_demo108_basic_minimal_script_regression(
    capsys, data_regression, cli_args, demo108_file, expected_output, expected_exit
):
    """Regression test that executes the actual script file using sh library."""

    # Get the path to the demo script
    demo_script = sh.Command(demo108_file)

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
