#!/usr/bin/env python3

"""
This is a demo of a main application with two subcommands. This example illustrates how to define subcommands.
"""

from clak import Parser, Argument, Command

class AppCommand1(Parser):
    "Command 1, which says hello"

    force = Argument('--force', '-f', action='store_true', help='Force')

    def cli_run(self, force=None, **_):
        print (f"Run Command 1: Hello")

class AppCommand2(Parser):
    "Command 2, with option and positional arguments"

    aliases = Argument('--alias', '-a', action='append', help='Alias')
    name = Argument('NAME', help='Name')

    def cli_run(self, name=None, aliases=None, force=False, config=None, **_):
        print (f"Run command 2 World on: {name} in '{config}' file (force_mode={force})")
        aliases = aliases or []
        for alias in aliases:
            print (f"Map: {alias} -> {name}")


class AppMain(Parser):
    """
    Demo application with options and two subcommands.

    This is a two levels demo of an application with two subcommands:

    - A subcommand: command1
    - A subcommand: command2
    """


    debug = Argument('--debug', action='store_true', help='Enable debug mode')
    config = Argument('--config', '-c', help='Config file path', default="config.yaml")
    
    # Define two subcommands
    command1 = Command(AppCommand1, help="Execute command 1")
    command2 = Command(AppCommand2, help='Execute command 2')


# Instanciate your app, parse command line and run appropiate command.
AppMain().dispatch()

