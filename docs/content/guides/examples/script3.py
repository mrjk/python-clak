#!/usr/bin/env python3

from clak import Argument, Command, Parser

class AppCommand1(Parser):  # (1)!
    "Command 1, which says hello"
    force = Argument("--force", "-f", action="store_true", help="Force")  # (2)!

    def cli_run(self, force=None, **_):  # (3)!
        force = "with the force" if force else "without the force"
        print(f"Run Command 1: Hello {force}")


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
    command1 = Command(AppCommand1, help="Execute command 1")  # (9)!
    command2 = Command(AppCommand2, help="Execute command 2")  # (10)!


if __name__ == "__main__":
    AppMain()
