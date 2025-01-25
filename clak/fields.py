
import argparse
from types import SimpleNamespace
from pprint import pprint
from clak.formatters import RecursiveHelpFormatter


class ArgParseItem(SimpleNamespace):
    """A argparse.argument item."""

    _destination: str = None



    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs




    @property
    def destination(self):
        "Var name"
        return self._get_best_dest()

    @destination.setter
    def destination(self, value):
        self._destination = value


    def _get_best_dest(self):

        if self._destination is not None:
            return self._destination

        # If no arguments, return None
        if not self.args:
            return None
            # raise ValueError(f"No key arguments found for {self.__class__.__name__}: {self.__dict__}")
            
        # Get first argument which should be the flag name
        arg = self.args[0]
        
        # Remove leading dashes and convert remaining dashes to underscores
        if arg.startswith('--'):
            key = arg[2:].replace('-', '_')
        elif arg.startswith('-'):
            # For short flags like -v, use the longer version if available
            if len(self.args) > 1 and self.args[1].startswith('--'):
                key = self.args[1][2:].replace('-', '_')
            else:
                key = arg[1:]
        else:
            key = arg.replace('-', '_')
            
        return key

    def build_params(self, dest:str):

        # dest = self.destination
        # dest = key

        # Create parser arguments
        if self.args:
            if len(self.args) > 2:
                raise ValueError(f"Too many arguments found for {self.__class__.__name__}: {self.__dict__}")
            args = self.args
        elif dest:
            if len(dest) <= 2:
                args =(f"-{dest}",)
            else:
                args = (f"--{dest}",)

        else:
            raise ValueError(f"No arguments found for {self.__class__.__name__}: {self.__dict__}")
        
        # Create parser
        kwargs = self.kwargs

        # Update dest if forced
        if dest:
            kwargs['dest'] = dest

        return args, kwargs    



class Argument(ArgParseItem):
    """A argparse.argument arguments."""
    

    def create_arg(self, key, config):

        parser = config.parser
        args, kwargs = self.build_params(key)
        assert isinstance(args, tuple), f"Args must be a list for {self.__class__.__name__}: {type(args)}"

        # Create parser
        print("Create new parser", self.__class__.__name__, args, kwargs)
        conf_errors = [ x for x in args if not x.startswith('-')]
        assert len(conf_errors) == 0, f"Missing args for {self.__class__.__name__}: {conf_errors}"
        parser.add_argument(*args, **kwargs)

        return parser


class Command(ArgParseItem):
    """A argparse.argument sub command."""

    def __init__(self, cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cls = cls

    def create_arg(self, key, config):
        if ' ' in key:
            raise ValueError(f"Command name '{key}' contains spaces. Command names must not contain spaces.")
        
        args, kwargs = self.build_params(key)
        pprint(self.__dict__)

        config2 = self.cls()
        self.add_parser(key, config2, config)
        return config2

    def add_parser(self, key: str, other_parser: 'ArgumentParserPlus', parent_config: 'ArgumentParserPlus', help: str = None):
        """Add another ArgumentParserPlus instance as a subparser with the given key.
        
        Args:
            key: The command name for this subparser
            other_parser: Another ArgumentParserPlus instance to add as a subparser
            parent_config: The parent ArgumentParserPlus instance where to add the subparser
            help: Help text for this command
        """
        subparser = parent_config.subparsers.add_parser(key, help=help, conflict_handler='resolve')
        
        # Copy all arguments from the other parser
        for action in other_parser.parser._actions:
            if not isinstance(action, argparse._SubParsersAction):
                subparser._add_action(action)
        
        # Copy subparsers if they exist
        for action in other_parser.parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                sub_subparsers = subparser.add_subparsers(dest='cmd', help=f'{key} commands')
                for choice, choice_parser in action.choices.items():

                    print("Create new subparser", choice, choice_parser)


                    sub_choice_parser = sub_subparsers.add_parser(
                        choice,
                        help=self.kwargs.get('help', ""),   # f"No help for {choice}"),
                        formatter_class=RecursiveHelpFormatter,
                        conflict_handler='resolve'
                    )

                    # Copy all actions from the choice parser
                    for sub_action in choice_parser._actions:
                        if not isinstance(sub_action, argparse._HelpAction):
                            sub_choice_parser._add_action(sub_action)







