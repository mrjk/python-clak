import sys
import argparse
from clak import Parser, Argument, Command
from pprint import pprint



# python examples/demo1.py computer -D https://itsm.example.org add mydomain.com -o rob -d "Yeahh"


class ItemAction(Parser):
    "Manage action on one item"

    description = Argument('--desc', '-d', help='Item description')
    owner = Argument('--owner', '-o', help='Item owner')

    name = Argument('target', help='Target to select')

    def cli_run(self, ctx, target=None, owner=None, desc=None, database_uri=None, kind=None, action=None, **kwargs):

        kind = kind if kind else ctx.cli_commands[-2]
        action = action if action else ctx.cli_commands[-1]

        words = "this"
        if action == "add":
            words = "new"
        elif action == "remove":
            words = "existing"
        owner_str = f"(owned by {owner})" if owner else ""            
        print (f"{action.capitalize()} {words.upper()} {kind} {owner_str}: {target}")

        if desc:
            print (f"Description: {desc}")
        if database_uri:
            print (f"Updating server: {database_uri}")

        pprint(self.__dict__)
        pprint(ctx)

class ManageItems(Parser):
    "Manage items"

    database_uri = Argument('--db', '-D', help='Database URI', default='http://localhost:8080')

    add = Command(ItemAction, help='Add item')
    remove = Command(ItemAction, help='Remove item')
    show = Command(ItemAction, help='Show item')


class ForwardCommand(Parser):
    """Automatic item forwarder"""

    target = Argument('--target', '-t', help='Target to show')
    format = Argument('--format', choices=['json', 'text'], help='Output format')

    kind = Argument('kind', choices=['phone', 'computer', 'camera', 'tablet'], help='Kind of item')
    action = Argument('action', choices=['add', 'remove', 'show'], help='Action to perform')
    name = Argument('NAME', help='Name of the item')

    def cli_run(self, ctx, kind=None, action=None, name=None, **_):
        print (f"Showing {kind}")

        pprint(ctx)

        if kind in ["phone", "computer"]:
            # TOFIX not implemented yet
            # There is no way to do that in current implementation.
            print("Redirect to another command")
            func = ctx.cli_root[kind][action].cli_run

            func(
                    ctx,
                    target=name, 
                    owner="rob", 
                    desc="Yeahh",
                    database_uri="https://itsm.example.org",
                    kind="phone", action="add")
            return
        
        print (f"Unknown kind: {kind}")
        sys.exit(1)
    
            
class MainApp(Parser):
    "Main application"

    class Meta:
        "Store Main app settings"
        help_description = "Hellow World of CLI !"
        help_epilog = "This is my epilog"

    debug = Argument('--debug', action='store_true', help='Enable debug mode')
    config = Argument('--config', '-c', help='Config file path')
    
    # Define subcommands
    computer = Command(ManageItems, help=argparse.SUPPRESS)
    phone = Command(ManageItems, help='Manage phones')

    # A more flattened command
    auto = Command(ForwardCommand, help='Show something')


# Instanciate your app, parse command line and run appropiate command.
MainApp().dispatch()

