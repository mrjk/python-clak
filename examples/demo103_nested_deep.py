#!/usr/bin/env python3

"""
This is a demo of a main application with two subcommands. This example illustrates how to define subcommands.

Purpose: 
  - Illustrate many sublevel subcommands
"""

from clak import Parser, Argument, Command


class AppSubAction(Parser):
    "Default action to illustrate subcommand reusability"

    def cli_run(self, args, **_):
        print (f"Command called with args: {args}")

class SubSubCommand2a(AppSubAction, Parser):
    "SubSubCommand2a"

    args = Argument('ARGS', nargs='+', help='One or more arguments')

class SubSubCommand2b(Parser):
    """SubSubCommand2b, should raise NotIMplemented error
    
    This happen because cli_run is not inherited"""

    args = Argument('ARGS', nargs='*', help='Zero or more arguments')


class SubCommand1(AppSubAction, Parser):
    "SubCommand1"

    args = Argument('ARGS', nargs='*', help='Zero or more arguments')

class SubCommand2(AppSubAction, Parser):
    "SubCommand2"

    sub2a = Command(SubSubCommand2a)
    sub2b = Command(SubSubCommand2b)


# Top level commands
class AppCommand1(Parser):
    "Command 1, which says hello"

    force = Argument('--force', '-f', action='store_true', help='Force')
    name = Argument('NAME', help='Name')

    sub1 = Command(SubCommand1)
    sub2 = Command(SubCommand2)

    def cli_run(self, force=None, name=None, **_):
        print (f"Run Command 1: Hello {name}")

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
    Demo application with options and many nested subcommands.
    """


    debug = Argument('--debug', action='store_true', help='Enable debug mode')
    config = Argument('--config', '-c', help='Config file path', default="config.yaml")
    
    # Define two subcommands
    command1 = Command(AppCommand1, help="Execute command 1")
    command2 = Command(AppCommand2, help='Execute command 2')


    def cli_run(self, **_):
        "Override default behavior"

        print ("When cli_run method is not explicitly defined, it show help if it has ")
        print( "Subcommands, otherwise it would have raised and NotImplemetedError error.\n\n")


        print("For example, we can decide to who usage instead of long help:")
        print("--- 8< --- 8< --- 8< ---")
        self.show_usage()
        print("--- 8< --- 8< --- 8< ---")

        print("\n\nBut this is not very conveniant for command discovery.")
        print("So let's show again long help:")
        print("--- 8< --- 8< --- 8< ---")
        self.show_help()
        print("--- 8< --- 8< --- 8< ---")



# Instanciate your app, parse command line and run appropiate command.
AppMain().dispatch()

