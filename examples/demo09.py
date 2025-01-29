
from clak import Parser, Argument, Command

class AppMain(Parser):
    "Main application with two arguments"

    # Option examples
    config  = Argument('--config', '-c', help='Config file path', default="config.yaml")
    # Define position arguments
    name = Argument('NAME', help='First Name', nargs='?')

    # Define our command, with arguments
    def cli_run(self, config=None, name=None, **_):

        if name is None:
            print("No name provided, please provide a name as first argument.")
            return
        print(f"Store name '{name}' in config file: {config}")

# Instanciate your app, parse command line and run appropiate command.
AppMain().dispatch()

