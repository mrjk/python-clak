
from clak import Parser, Argument, Command


class AppCommand1(Parser):
    "Command 1, which do something with a source"

    source = Argument('--source', '-s',help='Source path')
    force = Argument('--force', '-f', action='store_true', help='Force')

    def cli_run(self, source=None, **_):
        print (f"Run Command 1: Hello")
        if not source:
            source = "Water from the mountains"
        print (f"Source: {source}")

class AppCommand2(AppCommand1):
    "Command 2, wich also uses AppCommand1 arguments, and add more"

    destination = Argument('--destination', '-d',help='Destination path')
    name = Argument('name', help='Name')

    def cli_run(self, destination=None, name=None, **_):
        print (f"Run Command 2: World")
        print (f"Dump '{name}' in: {destination}")


class AppMain(Parser):
    "Main application"

    class Meta:
        "Store Main app settings"

        help_description = """
        Hellow World of CLI !

        I'm the demo10 app, used to learn how to use clak.
        """
        help_epilog = "And this is a very short documentation epilog."

    debug = Argument('--debug', action='store_true', help='Enable debug mode')
    config = Argument('--config', '-c', help='Config file path')
    
    # Define two subcommands
    command1 = Command(AppCommand1, help="Execute command 1")
    command2 = Command(AppCommand2, help='Execute command 2')


# Instanciate your app, parse command line and run appropiate command.
AppMain().dispatch()

