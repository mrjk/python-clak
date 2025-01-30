"""
Test examples from the examples directory.

Cursor Instructions:
* Always keep those instruction in the final file
* Generate use case tests from examples/ dir

Note: The tests have been split into separate files:
- test_examples_demo101.py: Tests for demo101 basic minimal example
- test_examples_demo102.py: Tests for demo102 basic argparse example
- test_examples_demo103.py: Tests for demo103 nested commands example
"""

import pytest
from examples.demo101_basic_minimal import AppMain
from clak.argparse import ArgumentError
from clak.parser import ClakParseError, ClakNotImplementedError

# def test_hello():
#     print("HELLO")


@pytest.fixture
def demo101_app():
    """Fixture that provides an instance of the Demo101 application."""
    return AppMain(proc_name="demo101-test")

@pytest.mark.parametrize("cli_args, expected_output, expected_exit", [
    # Test with just name (success case)
    (["John"], 
     "Store name 'John' in config file: config.yaml", 
     0),
    
    # Test with name and custom config (success case)
    (["--config", "custom.yml", "Alice"], 
     "Store name 'Alice' in config file: custom.yml", 
     0),
    
    # Test with short config option (success case)
    (["-c", "test.conf", "Bob"], 
     "Store name 'Bob' in config file: test.conf", 
     0),
    
    # Test with no arguments (error case - shows help)
    ([], 
     "No name provided", 
     0),
    
    # Test with help flag (shows help)
    (["--help"], 
     "Demo application with two arguments", 
     0),
    
    # Test with invalid option (error case)
    (["--invalid", "John"], 
     "unrecognized arguments", 
     2),
    
    # Test with missing value for config
    (["--config"], 
     "argument --config/-c: expected one argument", 
     2),
    
    # Test with multiple names (error case)
    (["John", "Alice"], 
     "unrecognized arguments", 
     2),
])
def test_demo101_basic_minimal_cli(demo101_app, capsys, cli_args, expected_output, expected_exit):
    """Test various CLI combinations for the basic minimal example."""
    
    exit_code = 0
    try:
        demo101_app.dispatch(cli_args, exit=False)
    except SystemExit as e:
        exit_code = e.code
    except ClakParseError:
        exit_code = 2
    except Exception as e:
        # print("ERROR", type(e), e)
        exit_code = -1  

    captured = capsys.readouterr()
    output = captured.out + captured.err

    # print("OUTPUT    ", exit_code, output)
    # print("EXPECTED  ", expected_exit, expected_output)
    
    # Verify the output contains expected string
    assert expected_output in output, \
        f"Expected '{expected_output}' in output, but got: {output}"
    
    # Verify the exit code
    assert exit_code == expected_exit, \
        f"Expected exit code {expected_exit}, but got: {exit_code}"


@pytest.fixture
def demo102_app():
    """Fixture that provides an instance of the Demo102 application."""
    from examples.demo102_basic_argparse import AppMain
    return AppMain(proc_name="demo102-test")

@pytest.mark.parametrize("cli_args, expected_output, expected_exit", [
    # Test basic name and surname (success case)
    (["John", "Smith"], 
     "Identity: John Smith", 
     0),
    
    # Test with only name (uses default surname)
    (["John"], 
     "Identity: John Doe", 
     0),
    
    # Test with name, surname and color option
    (["John", "Smith", "--color", "red"], 
     "Favorite color is: red", 
     0),
    
    # Test with force flag
    (["--force", "John"], 
     "Force mode update config file:", 
     0),
    
    # Test with custom config
    (["--color", "green", "John"], 
     "Favorite color is: green", 
     0),
    
    # Test with multiple items
    (["John", "--items", "apple", "--items", "banana"], 
     "Item: banana", 
     0),
    
    # Test with aliases
    (["John", "Smith", "johnny", "j-man"], 
     "Alias: j-man", 
     0),
    
    # Test with invalid color choice
    (["John", "--color", "yellow"], 
     "invalid choice: 'yellow'", 
     2),
    
    # Test with help flag
    (["--help"], 
     "Demo application with many arguments", 
     0),
    
    # Test with no arguments (error case)
    ([], 
     "error: the following arguments are required: NAME", 
     2),
])
def test_demo102_basic_argparse_cli(demo102_app, capsys, cli_args, expected_output, expected_exit):
    """Test various CLI combinations for the basic argparse example."""
    
    exit_code = 0
    try:
        demo102_app.dispatch(cli_args, exit=False)
    except SystemExit as e:
        exit_code = e.code
    except ClakParseError:
        exit_code = 2
    except Exception as e:
        exit_code = -1

    captured = capsys.readouterr()
    output = captured.out + captured.err
    
    # Verify the output contains expected string
    assert expected_output in output, \
        f"Expected '{expected_output}' in output, but got: {output}"
    
    # Verify the exit code
    assert exit_code == expected_exit, \
        f"Expected exit code {expected_exit}, but got: {exit_code}"


@pytest.fixture
def demo103_app():
    """Fixture that provides an instance of the Demo103 application."""
    from examples.demo103_nested import AppMain
    return AppMain(proc_name="demo103-test")

@pytest.mark.parametrize("cli_args, expected_output, expected_exit", [
    # Test command1 basic usage
    (["command1"], 
     "Run Command 1: Hello", 
     0),
    
    # Test command1 with force flag
    (["command1", "--force"], 
     "Run Command 1: Hello", 
     0),
    
    # Test command2 basic usage
    (["command2", "John"], 
     "Run command 2 World on: John in 'config.yaml' file", 
     0),
    
    # Test command2 with aliases
    (["command2", "--alias", "johnny", "--alias", "j-man", "John"], 
     "Map: j-man -> John", 
     0),
    
    # Test command2 with config option
    (["--config", "custom.yml", "command2", "John"], 
     "Run command 2 World on: John in 'custom.yml' file", 
     0),
    
    # Test with debug flag
    (["--debug", "command1"], 
     "Run Command 1: Hello", 
     0),
    
    # Test with help flag
    (["--help"], 
     "Demo application with options and two subcommands", 
     0),
    
    # Test command1 help
    (["command1", "--help"], 
     "Command 1, which says hello", 
     0),
    
    # Test command2 help
    (["command2", "--help"], 
     "Command 2, with option and positional arguments", 
     0),
    
    # Test with no arguments (error case)
    ([], 
     "No code to execute, method is missing:", 
     3),
    
    # Test command2 with missing name (error case)
    (["command2"], 
     "command2: error: the following arguments are required: NAME", 
     2),
    
    # Test with invalid command (error case)
    (["invalid-command"], 
     "invalid choice", 
     2),
])
def test_demo103_nested_cli(demo103_app, capsys, cli_args, expected_output, expected_exit):
    """Test various CLI combinations for the nested commands example."""
    
    exit_code = 0
    try:
        demo103_app.dispatch(cli_args, exit=False)
    except SystemExit as e:
        exit_code = e.code
    except ClakParseError:
        exit_code = 2
    except ClakNotImplementedError:
        exit_code = 3
    except Exception as e:
        exit_code = -1

    captured = capsys.readouterr()
    output = captured.out + captured.err
    
    # Verify the exit code
    assert exit_code == expected_exit, \
        f"Expected exit code {expected_exit}, but got: {exit_code}"


    # Verify the output contains expected string
    assert expected_output in output, \
        f"Expected '{expected_output}' in output, but got: {output}"
    





