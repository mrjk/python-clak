#!/usr/bin/env python3


from clak import Argument, Command, Parser

# Base action class for reusability
class AppSubAction(Parser):
    "Default action to illustrate subcommand reusability"
    def cli_run(self, args, **_):
        print(f"Command called with args: {args}")

# Level 3 commands
class SubSubCommand2a(AppSubAction):
    "SubSubCommand2a"
    args = Argument("ARGS", nargs="+", help="One or more arguments")

class SubSubCommand2b(Parser):
    "SubSubCommand2b"
    args = Argument("ARGS", nargs="*", help="Zero or more arguments")

# Level 2 commands
class SubCommand1(AppSubAction):
    "SubCommand1"
    args = Argument("ARGS", nargs="*", help="Zero or more arguments")

class SubCommand2(AppSubAction):
    "SubCommand2"
    sub2a = Command(SubSubCommand2a)
    sub2b = Command(SubSubCommand2b)

# Level 1 commands
class AppCommand1(Parser):
    "Command 1, which says hello"
    force = Argument("--force", "-f", action="store_true", help="Force")
    name = Argument("NAME", help="Name")
    
    sub1 = Command(SubCommand1)
    sub2 = Command(SubCommand2)

    def cli_run(self, force=None, name=None, **_):
        print(f"Run Command 1: Hello {name}")

class AppMain(Parser):
    """Demo application with deep nested commands"""
    debug = Argument("--debug", action="store_true", help="Enable debug mode")
    config = Argument("--config", "-c", help="Config file path", default="config.yaml")

    command1 = Command(AppCommand1, help="Execute command 1")


if __name__ == "__main__":
    AppMain()
