

import argparse
from pprint import pprint

from clak.formatters import RecursiveHelpFormatter
from clak.fields import ArgParseItem, Argument, Command


class ArgumentParserPlus():
    """An extensible argument parser that can be inherited to add custom fields.
    
    This class is designed to be subclassed by developers who want to create
    their own argument parser with custom fields and behavior.
    """
    
    arguments_dict: dict[str, ArgParseItem] = {}
    children: dict = {}

    def __init__(self, description: str = None, add_help: bool = True ):
        self.parser = argparse.ArgumentParser(
            description=description,
            formatter_class=RecursiveHelpFormatter,
            add_help=add_help)
        
        # Create subparsers container
        self.subparsers = self.parser.add_subparsers(dest='cmd', help='Available commands')
        
        self.init_options()
        self.init_children()

    def init_options(self):
        """Add all options defined in the arguments_dict dictionary."""
        # Lookup in explicit dict
        arguments_dict = self.arguments_dict or {}

        # Add arguments from class attributes that are Argument instances
        for attr_name, attr_value in self.__class__.__dict__.items():
            if isinstance(attr_value, Argument):
                # Store the attribute name as the key in the Fn instance
                attr_value.destination = attr_name
                arguments_dict[attr_name] = attr_value

        # Create all options
        for key, arg in arguments_dict.items():
            arg.create_arg(key, self)

    def init_children(self):
        """Add all parsers defined in the children dictionary."""

        children_dict = self.children or {}

        # Add arguments from class attributes that are Argument instances
        for attr_name, attr_value in self.__class__.__dict__.items():
            if isinstance(attr_value, Command):
                # Store the attribute name as the key in the Fn instance
                attr_value.destination = attr_name
                children_dict[attr_name] = attr_value

        for key, arg in children_dict.items():
            arg.create_arg(key, self)

    def parse_args(self):
        return self.parser.parse_args()

