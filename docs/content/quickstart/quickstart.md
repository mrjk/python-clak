# Quickstart

Create a two-command hello-world. Save this as `hello.py`:

``` python title="hello.py" linenums="1"
#!/usr/bin/env python3

from clak import Argument, Command, Parser


class AppCommand1(Parser):  # (1)!
    """Command 1, which says hello."""

    force = Argument("--force", "-f", action="store_true", help="Force")  # (2)!

    def cli_run(self, force=None, debug=False, **_):  # (3)!
        print(f"Run Command 1: Hello force={force}")
        if debug:
            print("Debug mode enabled")


class AppCommand2(Parser):  # (4)!
    """Command 2, with option and positional arguments."""

    aliases = Argument("--alias", "-a", action="append", help="Alias")  # (5)!
    name = Argument("NAME", help="Name")

    def cli_run(self, name=None, aliases=None, force=False, config=None, **_):  # (6)!
        print(
            f"Run command 2 World on: {name} in '{config}' file "
            f"(force_mode={force})"
        )
        for alias in aliases or []:
            print(f"Map: {alias} -> {name}")


class AppMain(Parser):  # (7)!
    """Demo application with options and two subcommands."""

    debug = Argument("--debug", action="store_true", help="Enable debug mode")  # (8)!
    config = Argument(
        "--config", "-c", help="Config file path", default="config.yaml"
    )

    command1 = Command(AppCommand1)  # (9)!
    command2 = Command(AppCommand2)  # (10)!


if __name__ == "__main__":
    AppMain()  # (11)!
```

1. Subcommand parser — inherits from `Parser` like the root app.
2. Optional flag — same kwargs as `argparse.add_argument()`.
3. `cli_run` is what runs for this command; parameters match argument destinations.
4. Second subcommand parser.
5. Repeatable option via `action="append"`.
6. Parent options (`debug`, `config`) are available on child `cli_run` too.
7. Root application parser.
8. Global options live on the root and apply to every subcommand.
9. Bind a child with `Command(...)` (argparse subparser under the hood).
10. Second binding — the attribute name becomes the CLI name (`command2`).
11. Instantiating the root parses `sys.argv` and runs the matched command.

Make it executable (or call it with Python) and inspect help:

``` raw
$ python hello.py --help
usage: hello.py [-h] [--debug] [--config CONFIG] {command1,command2} ...

Demo application with options and two subcommands.

positional arguments:

subcommands:
  command1                  Command 1, which says hello.
  command2                  Command 2, with option and positional arguments.

options:
  -h, --help                  show this help message and exit
  --debug                     Enable debug mode (default: False)
  --config CONFIG, -c CONFIG  Config file path (default: config.yaml)
```

Try a few calls:

```bash
python hello.py command1 --force
python hello.py --debug command2 --alias nick Alice
```

## What next?

1. Walk through the [basic guide](../guides/guide_101.md), then
   [nested commands](../guides/guide_102.md).
2. Add a star feature when you need it:
   [Views](../docs/views.md),
   [Logging](../docs/logging.md),
   [Config](../docs/config.md),
   [Completion](../docs/completion.md),
   [Error handling](../docs/exceptions.md).
3. Browse the [feature overview](../docs/features.md) or the
   [API reference](../api/module.md).
