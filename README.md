# Clak

<p align='center'>
<img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python Version">
<img src="https://img.shields.io/badge/license-GPL%20v3-blue" alt="License">
</p>

Clak (Command Line avec Klass) is a Python library that simplifies the creation of complex command-line interfaces using a class-based approach. It extends Python's `argparse` to provide an elegant and maintainable way to define nested commands and arguments.

## Features

- Hierarchical command based structure built with python class. No need to learn a new framewok, just use Python!
- Easy to use, easy to extend, easy to understand. Focus on your app, not your CLI.
- Based on Python Argparser. All what your learned is still useful, you wont be lost as it follows the same syntax.
- Light and minimalistic, while providing standard features via optional components.

- 🎯 Class-based command-line interface definition
- 🌳 Easy nested subcommand creation
- 🔄 Automatic help formatting with command tree display
- 🎨 Clean and intuitive API for defining arguments
- 📦 Inheritance-based command organization
- 🚀 Built on top of Python's standard `argparse`


## Quick Start

Add `clak` to your project dependecies:

```bash
pip install clak

# If you use one of those
poetry add clak
pdm add clak
```

Here's a simple example showing how to create a simple git-like command structure:

```python demo.py
from clak import Parser, Argument, Command

class ShowCommand(Parser):
    target = Argument('--target', '-t', help='Target to show')
    format = Argument('--format', choices=['json', 'text'], help='Output format')

class MainApp(Parser):
    debug = Argument('--debug', action='store_true', help='Enable debug mode')
    config = Argument('--config', '-c', help='Config file path')
    
    # Define subcommands
    show = Command(ShowCommand, help='Show something', choices=['phone', 'email', 'address'])

# Instanciate your app, parse command line and run appropiate command.
MainApp().dispatch()
```

This will create a CLI with the following structure:

```bash
$ python demo.py --help
myapp [-h] [--debug] [--config CONFIG] {show} ...
  show [-h] [--target TARGET] [--format {json,text}]
```


## Detailed Highlights


- Argparse friendly:
  - Reuse as much as possible from argparse, but allow a new modular way to built CLI.
  - If you know argparse, then you already know how to use clak.
  - Same API:
    - `argparse.ArgumentParser()` becomes `class MyApp(Parser):`
    - `.add_argument(...)` becomes `dest = Argument(...)`
    - `.add_subparser(...)` becomes `subcmd1 = SubCommand(...)`
  - Extended API:
    - `.add_argument("--option", "o", help="Optional argument")` => `option = Opt("--option", "o", help="Optional argument")`
    - `.add_argument("param", help="Positional argument")` => `param = Arg(help="Positional argument")`
    - `.add_suparser(...)` => `subcmd1 = Cmd(ChildrenParserClass, help="Subcommand help")`

- Class based approach:
  - Use Python class to provide declarative command line.
  - Since we use class, we can take advantage of Python inheritance to create CLI.
    - Including organizing command in a tree structure.
    - Inherit and share settings among different class, to allow maximum reusability.
  - Hide internal argparse implementation from user, so you can focus on your app.

- Build git-like CLI with ease
  - Rely on arparse subparser functionality.
  - Pythonic class based approach to represent.
  - Each subcommands are `Parser` instances, referenced via the `SubCommand` field.

- Easy sub-command discovery
  - All possible command are show in the root help
  - All subcommands display indiviudal and customizable help message.

- Modular components and reusable components:
  - Help:
    - Comprehensive help message with command tree display.
    - Manage `--help` and `-h` flags.
    - Easily change usage, description or epilog
  - Logging:
    - Configure and enable Basic Logger
    - Provide per Node logger
    - Provide `--verbose` and `-v,-vv,-vvv` flags
  - Config:
    - Use XDG Base Directory Specification to provide config files and directory paths.
    - Load yaml, json, toml, ini files easily
  - Completion:
    - Provide `completion` or `--complete` flag to generate completion script.
    - Support most common shell via the `argcomplete` library.
  - More to come ...
    - Environment var support
    - Automatic app config reader/writer
  - Build your own:
    - Reuse your existing code, your favorite CLI options, put them in a library and ship it.

## Key Concepts

### Arguments

Define arguments using the `Argument` class:

```python
class MyCommand(ArgumentParserPlus):
    # As class attributes
    verbose = Argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # Or in __cli__dict__
    __cli__dict__ = {
        'output': Argument('--output', '-o', help='Output file')
    }
```

### Nested Commands

Create complex command hierarchies using the `Command` class:

```python
class MainApp(ArgumentParserPlus):
    # As class attributes
    status = Command(StatusCommand, help='Show status')
    
    # Or in __cli__dict__
    __cli__dict__ = {
        'config': Command(ConfigCommand, help='Configure settings')
    }
```

## Advanced Usage

Check the `examples/` directory in the source code for more complex examples including:
- Multi-level command nesting
- Argument inheritance
- Custom help formatting
- Command grouping

## TODO

Implementation:

- [ ] Use more argparse plugins mechanisms

Features:

- [ ] Add support for `argcomplete`
- [ ] Add support for argparse Argument groups
  - [Argument groups](https://docs.python.org/3/library/argparse.html#argument-groups)
  - [Mutual exclusive groups](https://docs.python.org/3/library/argparse.html#mutual-exclusion)
- [ ] Add support for intermixed arguments
  - [Intermixed arguments](https://docs.python.org/3/library/argparse.html#intermixed-arguments)
- [ ] Add support for `fire`

## Requirements

- Python 3.9 or higher
- argparse (built into Python)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GPL v3 License.
