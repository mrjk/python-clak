#!/usr/bin/env python3

"""
This is a demo of a main application with two subcommands. This example illustrates how to define subcommands and
reuse arguments from from other classes.

Purpose: 
  - Illustrate subcommands and arguments reusability via mixed class inheritance
"""

from clak import Argument, Command, Parser


class AppCommand1(Parser):
    "Command 1, which do something with a source"

    source = Argument("--source", "-s", help="Source path")
    force = Argument("--force", "-f", action="store_true", help="Force")

    def cli_run(self, source=None, **_):
        print(f"Run Command 1: Hello")
        if not source:
            source = "Water from the mountains"
        print(f"Source: {source}")


class AppCommand2(AppCommand1):
    "Command 2, wich also uses AppCommand1 arguments, and add more"

    destination = Argument("--destination", "-d", help="Destination path")
    name = Argument("name", help="Name")

    def cli_run(self, destination=None, name=None, **_):
        print(f"Run Command 2: World")
        print(f"Dump '{name}' in: {destination}")


class AppMain(Parser):
    """
    Demo application with options and two subcommands, and a common argument.

    This is a two levels demo of an application with two subcommands:

    - A subcommand: command1
    - A subcommand: command2, inherited from command1

    """

    debug = Argument("--debug", action="store_true", help="Enable debug mode")
    config = Argument("--config", "-c", help="Config file path", default="config.yaml")

    # Define two subcommands
    command1 = Command(AppCommand1, help="Execute command 1")
    command2 = Command(AppCommand2, help="Execute command 2")


if __name__ == "__main__":

    # Instanciate your app, parse command line and run appropiate command.
    AppMain()
