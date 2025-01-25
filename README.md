# Clak

<p align='center'>
<img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python Version">
<img src="https://img.shields.io/badge/license-GPL%20v3-blue" alt="License">
</p>

Clak (Command Line avec Klass) is a Python library that simplifies the creation of complex command-line interfaces using a class-based approach. It extends Python's `argparse` to provide an elegant and maintainable way to define nested commands and arguments.

## Features

- 🎯 Class-based command-line interface definition
- 🌳 Easy nested subcommand creation
- 🔄 Automatic help formatting with command tree display
- 🎨 Clean and intuitive API for defining arguments
- 📦 Inheritance-based command organization
- 🚀 Built on top of Python's standard `argparse`

## Installation

```bash
pip install clak
```

## Quick Start

Here's a simple example showing how to create a nested command structure:

```python
from clak import ArgumentParserPlus, Argument, Command

class ShowCommand(ArgumentParserPlus):
    target = Argument('--target', '-t', help='Target to show')
    format = Argument('--format', choices=['json', 'text'], help='Output format')

class MainApp(ArgumentParserPlus):
    debug = Argument('--debug', action='store_true', help='Enable debug mode')
    config = Argument('--config', '-c', help='Config file path')
    
    # Define subcommands
    show = Command(ShowCommand, help='Show something')

# Create and parse arguments
parser = MainApp()
args = parser.parse_args()
```

This will create a CLI with the following structure:
```
myapp [-h] [--debug] [--config CONFIG] {show} ...
  show [-h] [--target TARGET] [--format {json,text}]
```

## Key Concepts

### Arguments

Define arguments using the `Argument` class:

```python
class MyCommand(ArgumentParserPlus):
    # As class attributes
    verbose = Argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # Or in arguments_dict
    arguments_dict = {
        'output': Argument('--output', '-o', help='Output file')
    }
```

### Nested Commands

Create complex command hierarchies using the `Command` class:

```python
class MainApp(ArgumentParserPlus):
    # As class attributes
    status = Command(StatusCommand, help='Show status')
    
    # Or in children dict
    children = {
        'config': Command(ConfigCommand, help='Configure settings')
    }
```

## Advanced Usage

Check the `examples/` directory in the source code for more complex examples including:
- Multi-level command nesting
- Argument inheritance
- Custom help formatting
- Command grouping

## Requirements

- Python 3.9 or higher
- argparse (built into Python)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GPL v3 License.
