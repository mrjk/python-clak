# lib_dual.py

from types import SimpleNamespace
import argparse
import argcomplete
from pprint import pprint
import logging
import os

logger = logging.getLogger(__name__)

# Enable debug logging if CLAK_DEBUG environment variable is set to 1
if os.environ.get('CLAK_DEBUG') == '1':
    logging.basicConfig(level=logging.DEBUG,
    format='[%(levelname)8s] %(name)s - %(message)s',

                        )
    logger.debug("Debug logging enabled via CLAK_DEBUG environment variable")

from clak.argparse import RecursiveHelpFormatter, argparse_merge_parents, argparse_inject_as_subparser
from clak.nodes import Fn, Node

# Version: v6

# This version of the lib:
# Implement merge+inject methods
# Implement basic


# Argparser Merge Library
# ################################################################################

# Argparse helpers, portable library for argparse.

# Keep this as True for performance reasons,
# children nodes will be considered as subparsers and not other parsers to be
# injected into the parent parser. The latter is slower.

USE_SUBPARSERS = True
# USE_SUBPARSERS = False    # BETA - Do not enable this, it is slower

# ArgumentParserPlus Core library
# ################################################################################

# Top objects



class ArgParseItem(Fn):
    """A argparse.argument item."""

    _destination: str = None

    @property
    def destination(self):
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

        # Get first argument which should be the flag name
        arg = self.args[0]

        # Remove leading dashes and convert remaining dashes to underscores
        if arg.startswith("--"):
            key = arg[2:].replace("-", "_")
        elif arg.startswith("-"):
            # For short flags like -v, use the longer version if available
            if len(self.args) > 1 and self.args[1].startswith("--"):
                key = self.args[1][2:].replace("-", "_")
            else:
                key = arg[1:]
        else:
            key = arg.replace("-", "_")

        return key

    def build_params(self, dest: str):
        # Create parser arguments
        if self.args:
            if len(self.args) > 2:
                raise ValueError(
                    f"Too many arguments found for {self.__class__.__name__}: {self.__dict__}"
                )
            args = self.args
        elif dest:
            if len(dest) <= 2:
                args = (f"-{dest}",)
            else:
                args = (f"--{dest}",)
        else:
            raise ValueError(
                f"No arguments found for {self.__class__.__name__}: {self.__dict__}"
            )

        # Create parser
        kwargs = self.kwargs

        # Update dest if forced
        if dest:
            kwargs["dest"] = dest

        return args, kwargs


# Developper objects

class Argument(ArgParseItem):
    """A argparse.argument arguments."""

    def create_arg(self, key, config):
        parser = config.parser
        args, kwargs = self.build_params(key)
        assert isinstance(
            args, tuple
        ), f"Args must be a list for {self.__class__.__name__}: {type(args)}"

        # Create parser
        logger.debug("Create new argument %s.%s: %s", config.get_fname(attr="key"), key, self.kwargs)

        # logger.debug("Create new parser %s %s %s", self.__class__.__name__, args, kwargs)
        conf_errors = [x for x in args if not x.startswith("-")]
        
        if len(conf_errors) != 0:
            # There are positional args

            # Remove dest in kwargs
            if "dest" in kwargs:
                kwargs.pop("dest")
                # args = []
            

        parser.add_argument(*args, **kwargs)

        return parser


class SubParser(ArgParseItem):
    """A argparse.argument sub command."""


    # If true, enable -h and --help support
    meta__help_flags = True


    meta__usage = None
    meta__description = None
    meta__epilog = None


    def __init__(self, cls, *args, use_subparsers: bool = USE_SUBPARSERS, **kwargs):
        super().__init__(*args, **kwargs)
        self.cls = cls
        self.use_subparsers = use_subparsers

    def create_subcommand(self, key, config):

        if " " in key:
            raise ValueError(
                f"Command name '{key}' contains spaces. Command names must not contain spaces."
            )

        if self.use_subparsers:

            logger.debug("Create new subparser %s.%s", config.get_fname(attr="key"), key ) #, self.kwargs)

            # Fetch help from class
            child_help = self.kwargs.get("help",
                self.cls.query_cfg_inst(
                    self.cls, "help_description", 
                    default=self.cls.__doc__)
            )
            child_enabled = self.kwargs.get("help_flags", 
                self.cls.query_cfg_inst(
                    self.cls, "help_flags", 
                    default=True))
            

            # Create a new subparser for this command (flat structure)
            subparser = config.subparsers.add_parser(
                key,
                formatter_class=RecursiveHelpFormatter,
                add_help=child_enabled, # Add support for --help
                exit_on_error=False,
                help=child_help,
            )


            # Create an instance of the command class with the subparser
            child = self.cls(parent=config, parser=subparser, key=key)

            # logger.debug("Create new SUBPARSER %s %s %s", child.get_fname(attr="key"), key, self.kwargs)


            # Reconfigure subparser
            subparser.add_help = False #child.query_cfg_inst("help_enable", default=True)
            subparser.usage = child.query_cfg_inst("help_usage", default=None)
            subparser.description = child.query_cfg_inst("help_description", default=child.__doc__)
            subparser.epilog = child.query_cfg_inst("help_epilog", default=None)

            # pprint (subparser.__dict__)

            return child
        else:
            # This part is in BETA


            # Create nested structure
            child = self.cls(parent=config)
            # Pass help text from Command class kwargs
            child.parser.help = self.kwargs.get("help", child.__doc__)
            argparse_inject_as_subparser(config.parser, key, child.parser)

            return child


# Main parser object

class Parser(Node):
    """An extensible argument parser that can be inherited to add custom fields.

    This class is designed to be subclassed by developers who want to create
    their own argument parser with custom fields and behavior.
    """

    arguments_dict: dict[str, ArgParseItem] = {}
    children: dict[str, type] = {}  # Dictionary of subcommand name to subcommand class
    inject_as_subparser: bool = True


    meta__name: str = None

    def __init__(
        self,
        description: str = None,
        add_help: bool = True,
        parent: "Parser" = None,
        key: str = None,
        parser: argparse.ArgumentParser = None,
        inject_as_subparser: bool = True,
    ):

        self.parent = parent
        super().__init__(parent=parent)

        self.key = key
        self.inject_as_subparser = inject_as_subparser

        if parser is None:
            usage = self.query_cfg_parents("help_usage", default=None)      
            description = self.query_cfg_parents("help_description", default=self.__doc__)
            epilog = self.query_cfg_parents("help_epilog", default=None)
            self.parser = argparse.ArgumentParser(
                usage=usage,
                description=description,
                formatter_class=RecursiveHelpFormatter,
                add_help=add_help,
                epilog=epilog,
                exit_on_error=False,
            )
            self.proc_name = self.parser.prog
        else:
            self.parser = parser
            self.proc_name = self.parent.proc_name

        # pprint(self.parser.__dict__)

        self._subparsers = None

        self.init_options()
        self.init_subcommands()

    @property
    def subparsers(self):
        """Lazily create and return the subparsers object."""
        # if not self.inject_as_subparser:
        #     return self.parser

        if self._subparsers is None:
            self._subparsers = self.parser.add_subparsers(
                dest="cli_cmd", help="Available commands"
            )
        return self._subparsers

    def init_options(self):
        """Add all options defined in the arguments_dict dictionary."""
        # Start with explicit dict and add class attributes
        arguments = getattr(self, 'arguments_dict', {}) or {}
        
        # Add arguments from class attributes including inherited ones
        for cls in self.__class__.__mro__:
            for name, value in vars(cls).items():
                if isinstance(value, Argument) and name not in arguments:
                    value.destination = name
                    arguments[name] = value

        # Add cli_self argument
        arguments["cli_self"] = Argument(help=argparse.SUPPRESS, default=self)

        # Create all options
        for key, arg in arguments.items():
            arg.create_arg(key, self)

    def init_subcommands(self):
        """Add all parsers defined in the children dictionary."""
        children_dict = self.children or {}

        # Add arguments from class attributes that are Command instances
        for attr_name, attr_value in self.__class__.__dict__.items():
            if isinstance(attr_value, Command):
                # Store the attribute name as the key in the Fn instance
                attr_value.destination = attr_name
                children_dict[attr_name] = attr_value

        for key, arg in children_dict.items():
            arg.create_subcommand(key, self)

    def parse_args(self):
        parser = self.parser
        argcomplete.autocomplete(parser)

        return parser.parse_args()

    def show_help(self):
        self.parser.print_help()


    def cli_run(self, ctx, **kwargs):
        "Placeholder for cli_run"
        print(f"No code to execute, method is missing: {self.__class__.__name__}.cli_run(self, ctx, **kwargs)")
        raise NotImplementedError(f"No 'cli_run' method found for {self}")

    def cli_group(self, ctx, **kwargs):
        "Placeholder for cli_group"


    def dispatch(self):
        args = self.parse_args()
        # ctx = SimpleNamespace(**args.__dict__)
        ctx = {} #dict(args.__dict__)
        args = args.__dict__
        args = dict(sorted(args.items()))


        # Get node 
        cli_self = args.pop("cli_self")
        logger.debug("Run instance %s", cli_self)
        ctx["cli_self"] = cli_self
        ctx["args"] = SimpleNamespace(**args)
        ctx["data"] = {}
        ctx["plugins"] = {}
        ctx["cli_methods"] = None
        ctx["cli_first"] = True
        ctx["cli_state"] = None


        # Prepare nodes context
        name = self.query_cfg_parents("name")
        ctx["app_name"] = self.query_cfg_parents("app_name", default=name)
        ctx["app_file_name"] = self.query_cfg_parents("app_file_name", default=self.proc_name)
        

        ctx["app_env_prefix"] = self.query_cfg_parents("app_env_prefix", default=name.upper())
        
        # print ("OUT OPTIONS", out)

        hierarchy = cli_self.get_hierarchy()
        node_count = len(hierarchy)
        # print("Hierarchy %s", hierarchy)
        fn_group_name = "cli_group"
        fn_exec_name = "cli_run" # Or cli exec
        hook_list = {}

        # Execute all nodes in hierarchy
        for idx, node in enumerate(hierarchy):
            last_node = True if idx == node_count - 1 else False
            has_children = node._subparsers is not None

            logger.info(f"Processing node {idx}:{node}.{fn_group_name}")
            # print(f"Node {idx}:{node}")

            # Prepare hooks list
            cls_hooks = [ method for method in dir(self) if method.startswith("cli_hook__")]
            for hook_name in cls_hooks:
                if not hook_name in hook_list:
                    hook_fn = getattr(self, hook_name, None)
                    if hook_fn is not None:
                        # Hooks order should be preserved with dict
                        hook_list[hook_name] = hook_fn

            # print("\n\nHOOK LIST")
            # pprint(hook_list)

            # Update ctx with node attributes
            ctx["cli_parents"] = hierarchy[:idx]
            ctx["cli_children"] = hierarchy[idx+1:]
            ctx["cli_last"] = last_node
            ctx["cli_hooks"] = hook_list
            ctx["cli_index"] = idx
            ctx["cli_count"] = node_count
            

            # Sort ctx dict by keys before creating namespace
            sorted_ctx = dict(sorted(ctx.items()))
            _ctx = SimpleNamespace(**sorted_ctx)
            _ctx.cli_state = "run_hooks"

            # Process hooks
            for name, hook_fn in hook_list.items():
                # hook_fn = getattr(self, hook, None)
                # if hook_fn is not None:
                logger.info(f"Run hook {idx}:{node}.{name}")
                hook_fn(node, _ctx)
            _ctx.cli_methods = getattr(node, "cli_methods", {})


            # Run group_run
            _ctx.cli_state = "run_groups"

            group_fn = getattr(node, fn_group_name, None)
            # print ("GROUP FN", group_fn)
            if group_fn is not None:
                logger.info(f"Group function execute: {idx}:{node}.{fn_group_name}")
                group_fn(ctx=_ctx, **_ctx.__dict__)

            # Run leaf only if last node
            _ctx.cli_state = "run_exec"
            if last_node is True:
                run_fn = getattr(node, fn_exec_name, None)

                if run_fn is None:
                    if has_children is True:
                        logger.info(f"Parent group default help: {idx}:{node}")
                        # TOFIX: This behavior should be a parameter
                        # print ("GROUP COMMAND NOT IMPLEMENTED")
                        node.show_help()
                        # TOFIX: Sys.exit(1)
                        return
                    # pprint(_ctx)
                    raise NotImplementedError(f"No '{fn_exec_name}' function found for {node}")

                logger.info(f"Run function execute: {idx}:{node}.{fn_exec_name}")
                run_fn(ctx=_ctx, **_ctx.__dict__)
            
            # Change status
            ctx["cli_first"] = False

# # Compatibility
ArgumentParserPlus = Parser
ArgParser = Parser
Command = SubParser

# # Argparse mode
# ArgumentParser()
# Argument()
# SubParser()

# # Clak mode:
# ClakParser()
# Opt()
# Arg()
# Cmd()
