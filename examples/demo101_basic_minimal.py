#!/usr/bin/env python3
"""
This is a single level demo of an application with two arguments.

Purpose: 
  - Show a very basic command line
"""

from clak import Argument, Command, Parser


class AppMain(Parser):
    """
    Demo application with two arguments.

    This is a single level demo of an application with two arguments:

    - An option Argument: config
    - A positional argument: name
    """

    # Option examples
    config = Argument("--config", "-c", help="Config file path", default="config.yaml")
    # Define positional arguments
    name = Argument("NAME", help="First Name", nargs="?")

    # Define our command, with arguments
    def cli_run(self, config=None, name=None, **_):
        "The cli_run method holds the code to run"

        if name is None:
            print("No name provided, please provide a name as first argument.")
            return
        print(f"Store name '{name}' in config file: {config}")

        print(f"AppMain.__doc__: {__name__.__doc__}")
        # Show the file docstring message
        print(f"File docstring message: {__doc__}")


if __name__ == "__main__":
    # Instanciate your app, parse command line and run appropiate command.
    AppMain().dispatch()
