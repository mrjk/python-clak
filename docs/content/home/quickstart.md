# Quickstart

To create an 2 commands hello world example, create a new `demo.py` file with this content:

``` python title="hello.py" linenums="1"
#!/usr/bin/env python3

from clak import Parser, Argument, Command

class AppCommand1(Parser):  # (1)!
    "Command 1, which says hello"
    force = Argument("--force", "-f", action="store_true", help="Force")  # (2)!

    def cli_run(self, force=None, debug=False, **_):  # (3)!
        print(f"Run Command 1: Hello force={force}")
        if debug:
            print("Debug mode enabled")

class AppCommand2(Parser):  # (4)!
    "Command 2, with option and positional arguments"
    aliases = Argument("--alias", "-a", action="append", help="Alias")  # (5)!
    name = Argument("NAME", help="Name")

    def cli_run(self, name=None, aliases=None, force=False, config=None, **_):  # (6)!
        print(f"Run command 2 World on: {name} in '{config}' file (force_mode={force})")
        for alias in aliases or []:
            print(f"Map: {alias} -> {name}")

class AppMain(Parser):  # (7)!
    """Demo application with options and two subcommands."""
    debug = Argument("--debug", action="store_true", help="Enable debug mode")  # (8)!
    config = Argument("--config", "-c", help="Config file path", default="config.yaml")

    # Define subcommands
    command1 = Command(AppCommand1)  # (9)!
    command2 = Command(AppCommand2)  # (10)!

if __name__ == "__main__":
    AppMain()
```

Make it executable (or call it with python interpreter) and try command flags:

``` raw
python demo.py --help
usage: demo.py [-h] [--debug] [--config CONFIG] {command1,command2} ...

Demo application with options and two subcommands.

positional arguments:

subcommands:
  command1                  Execute command 1
  command2                  Execute command 2

options:
  -h, --help                  show this help message and exit
  --debug                     Enable debug mode (default: False)
  --config CONFIG, -c CONFIG  Config file path (default: config.yaml)

```

## What next ?

You can either follow the [guides](guides/) or dive into the technical [documentation](docs).

Reference documentation is available in the [API reference](reference/).