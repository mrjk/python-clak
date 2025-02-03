#!/usr/bin/env python3

"""
This is a single level application with multiple arguments. It illustrates basic argparse usages.

Purpose: 
  - Illustrate argparse usage

"""

from clak import Argument, Command, Parser


class AppMain(Parser):
    """
    Demo application with many arguments.

    This is a single level demo of an application with many argparse arguments:
      - An option Argument: force
      - An option Argument: config
      - An option Argument: color
      - An option Argument: items
      - A positional argument: name
      - A positional argument: surname
      - A positional argument: aliases
    """

    # Option examples
    force = Argument("--force", "-f", action="store_true", help="Force mode")
    config = Argument("--config", "-c", help="Config file path", default="config.yaml")
    color = Argument(
        "--color",
        "-r",
        choices=["red", "green", "blue", "unknown"],
        default="unknown",
        help="Favorite color",
    )
    items = Argument("--items", "-m", action="append", help="Preferred items")

    # Define position arguments
    name = Argument("NAME", help="First Name")
    surname = Argument("SURNAME", nargs="?", default="Doe", help="Last Name")
    aliases = Argument("ALIAS", nargs="*", default="Doe", help="Aliases")

    def cli_run(
        self,
        name=None,
        surname=None,
        color=None,
        aliases=None,
        items=None,
        force=False,
        config=None,
        **_,
    ):
        """
        Run the application
        """

        if force:
            print(f"Force mode update config file: {config}")
        else:
            print(f"No force mode, config file: {config}")

        print(f"Identity: {name} {surname or 'MISSING_SURNAME'}")
        print(f"Favorite color is: {color}")
        for alias in aliases or []:
            print(f"  Alias: {alias}")

        for item in items or []:
            print(f"  Item: {item}")


if __name__ == "__main__":
    # Instanciate your app, parse command line and run appropiate command.
    AppMain()
