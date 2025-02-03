#!/usr/bin/env python3

from clak import Argument, Parser  # (1)!


class AppMain(Parser):  # (2)!
    """Demo application with two arguments."""  # (3)!

    config = Argument(
        "--config", "-c", help="Config file path", default="config.yaml"  # (4)!
    )
    name = Argument("NAME", help="First Name", nargs="?")  # (5)!

    def cli_run(self, config=None, name=None, **_):  # (6)!
        """The cli_run method holds the code to run"""

        if name is None:
            print("No name provided, please provide a name as first argument.")
            self.cli_exit(1)  # (7)!

        print(f"Store name '{name}' in config file: {config}")


if __name__ == "__main__":
    AppMain()  # (8)!
