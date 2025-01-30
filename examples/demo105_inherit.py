#!/usr/bin/env python3

"""
This is a demo of a main application with two subcommands. This example illustrates how to define subcommands and
reuse arguments from from other classes.

Purpose: 
  -Illustrate subcommands and arguments reusability via Python class inheritance
"""

from clak import Parser, Argument, Command


class CommonOptions(Parser):
    "Common options for all commands"

    source = Argument('--source', '-s',help='Source path')
    force = Argument('--force', '-f', action='store_true', help='Force')

class AppCommand1(CommonOptions):
    "Command 1, which do something with a source"

    def cli_run(self, source=None, **_):
        print (f"Run Command 1: Hello")
        if not source:
            source = "Water from the mountains"
        print (f"Source: {source}")

class AppCommand2(CommonOptions):
    "Command 2, wich also uses AppCommand1 arguments, and add more"

    destination = Argument('--destination', '-d',help='Destination path')
    name = Argument('name', help='Name')

    def cli_run(self, destination=None, name=None, **_):
        print (f"Run Command 2: World")
        print (f"Dump '{name}' in: {destination}")


class AppMain(Parser):
    """
    Demo application with options and two subcommands.

    This is a two levels demo of an application with two subcommands:

    - A subcommand: command1, args inherited from CommonOptions
    - A subcommand: command2, args inherited from CommonOptions
    """

    debug = Argument('--debug', action='store_true', help='Enable debug mode')
    config = Argument('--config', '-c', help='Config file path', default="config.yaml")
    
    # Define two subcommands
    command1 = Command(AppCommand1, help="Execute command 1")
    command2 = Command(AppCommand2, help='Execute command 2')


# Instanciate your app, parse command line and run appropiate command.
AppMain().dispatch()

