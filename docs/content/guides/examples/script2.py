#!/usr/bin/env python3

from clak import Argument, Parser  # (1)!


class AppMain(Parser):
    """Demo application with many arguments."""

    # Boolean flag
    force = Argument("--force", "-f", action="store_true", help="Force mode")  # (2)!

    # String with default
    config = Argument("-c", help="Config file path", default="config.yaml")  # (3)!

    # Choice from predefined options
    color = Argument(
        "--color",  # (4)!
        choices=["red", "green", "blue", "unknown"],
        default="unknown",
        help="Favorite color",
    )

    # List of items (can be specified multiple times)
    items = Argument("--items", "-m", action="append", help="Preferred items")  # (5)!

    # Required positional argument
    name = Argument("NAME", help="First Name")  # (6)!

    # Optional positional with default
    surname = Argument("SURNAME", nargs="?", default="Doe", help="Last Name")  # (7)!

    # List of remaining arguments
    aliases = Argument(
        "ALIAS", nargs="*", default=["Bond", "agent 007"], help="Aliases"  # (8)!
    )

    def cli_run(  # (9)!
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
        """Run the application"""
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
    AppMain()  # (10)!
