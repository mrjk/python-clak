# lib_dual.py

import sys
from types import SimpleNamespace
from typing import Sequence
# import argparse
import argcomplete
import traceback
from pprint import pprint
import logging
import os

logger = logging.getLogger(__name__)

# Enable debug logging if CLAK_DEBUG environment variable is set to 1
CLAK_DEBUG = False
if os.environ.get('CLAK_DEBUG') == '1':
    logging.basicConfig(level=logging.DEBUG,
    format='[%(levelname)8s] %(name)s - %(message)s',
                        )
    logger.debug("Debug logging enabled via CLAK_DEBUG environment variable")
    CLAK_DEBUG = True

import clak.exception as exception
from clak.common import deindent_docstring
from clak.argparse import _argparse as argparse, SUPPRESS
from clak.argparse import RecursiveHelpFormatter, argparse_merge_parents, argparse_inject_as_subparser
from clak.nodes import Fn, Node, NOT_SET



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


        # Create parser
        kwargs = self.kwargs

        kind = "option"
        if len(self.args) > 0:
            if len(self.args) > 2:
                raise ValueError(
                    f"Too many arguments found for {self.__class__.__name__}: {self.args}"
                )
            
            args = self.args

            arg1 = args[0]
            if not arg1.startswith("-"):
                # Remove first position arg to avoid argparse error:
                # ValueError: dest supplied twice for positional argument

                kwargs["metavar"] = args[0]
                args = ()
                kind = "argument"



        elif dest:
            if len(dest) <= 2:
                args = (f"-{dest}",)
            else:
                args = (f"--{dest}",)
        else:
            raise ValueError(
                f"No arguments found for {self.__class__.__name__}: {self.__dict__}"
            )


        # TOFIX
        # Update dest if forced
        if dest:
            kwargs["dest"] = dest

        # if kind == "argument":
        #     if "dest" in kwargs:
        #         if len(args) == 1:
        #             # Remove first position arg to avoid argparse error:
        #             # ValueError: dest supplied twice for positional argument
        #             kwargs["metavar"] = args[0]
        #             args = ()
        #         else:
        #             raise ValueError(f"Too many arguments found for {self.__class__.__name__}: {self.__dict__}")

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
        # conf_errors = [x for x in args if not x.startswith("-")]
        
        # if len(conf_errors) != 0:
        #     # There are positional args

        #     # Remove dest in kwargs
        #     if "dest" in kwargs:
        #         kwargs.pop("dest")
        #         # args = []

        # print ("ARGS", config, key, args, kwargs)
        # parser.add_argument(*args, clak_config="YEAH", **kwargs)
        parser.add_argument(*args, **kwargs)

        dest = kwargs["dest"]
        # config.registry[dest] = parser
        # pprint(config.registry[config.fkey])

        # pprint(config.registry)

        # config._fields_index[dest] = self
        # config.registry[config.fkey].add_entry(dest, self)

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
            parser_help = self.kwargs.get("help",
                self.cls.query_cfg_inst(
                    self.cls, "help_description", 
                    default=self.cls.__doc__)
            )
            parser_help_enabled = self.kwargs.get("help_flags", 
                self.cls.query_cfg_inst(
                    self.cls, "help_flags", 
                    default=True))
            
            ctx_vars = {
                "key": key, 
                "self": config
            }

            # Create a new subparser for this command (flat structure)
            parser_help = prepare_docstring(first_doc_line(parser_help), variables=ctx_vars)
            parser_kwargs = {
                "formatter_class": RecursiveHelpFormatter,
                "add_help": parser_help_enabled, # Add support for --help
                "exit_on_error": False,
                "help": parser_help,
            }
            # if parser_help is not None:
            #     parser_kwargs["help"] = parser_help

            # Create parser
            subparser = config.subparsers.add_parser(
                key,
                **parser_kwargs,
            )

            # Create an instance of the command class with the subparser
            child = self.cls(parent=config, parser=subparser, key=key)
            ctx_vars["self"] = child

            # logger.debug("Create new SUBPARSER %s %s %s", child.get_fname(attr="key"), key, self.kwargs)

            child_usage = child.query_cfg_inst("help_usage", default=None)
            child_desc = first_doc_line(child.query_cfg_inst("help_description", default=child.__doc__))
            child_epilog = child.query_cfg_inst("help_epilog", default=None)
            # print(f"DESC: |{desc}|")

            # Reconfigure subparser
            child_usage = prepare_docstring(child_usage, variables=ctx_vars)
            child_desc = prepare_docstring(child_desc, variables=ctx_vars)
            child_epilog = prepare_docstring(child_epilog, variables=ctx_vars)

            subparser.add_help = False #child.query_cfg_inst("help_enable", default=True)
            subparser.usage = child_usage
            subparser.description = child_desc
            subparser.epilog = child_epilog

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


class RegistryEntry():
    "Registry entry"

    def __init__(self, config):
        # super().__init__(*args, **kwargs)
        # self.parser = None
        self._config = config
        self._entries = {}


    def add_entry(self, key, value):
        self._entries[key] = value

    def __repr__(self):
        return f"RegistryEntry({self._config})"

def first_doc_line(text):
    "Get first line of text, ignore empty lines"
    lines = text.split("\n")
    for line in lines:
        if line.strip():
            assert not line.startswith(" "), f"First line of docstring should not start with 2 spaces: {line}"
            return line
    return ""

def prepare_docstring(text, variables=None, reindent=""):
    "Prepare docstring"

    variables = variables or {}
    assert isinstance(variables, dict), f"Got {type(variables)} instead of dict"

    if text is None:
        return None
    if text == SUPPRESS:
        return SUPPRESS


    text = deindent_docstring(text, reindent=reindent)
    try:
        text = text.format(**variables)
    except KeyError as e:
        print (f"Error formatting docstring: {e}")
        print (f"Variables: {variables}")
        print (f"Text: {text}")
        raise e

    return text

class FormatEnv(dict):
    "Format env"

    _default = {
        "type": "type FUNC",
    }

    def __init__(self, variables=None):
        self._variables = variables or {}

    # def __str__(self):
    #     return self.value.format(**self.variables)

    def get(self):
        "Get dict of vars"
        out = {}
        out.update(self._default)
        out.update(self._variables)
        return out

    def __dict__(self):
        return dict(self.get())



# Main parser object




class Parser(Node):
    """An extensible argument parser that can be inherited to add custom fields.

    This class is designed to be subclassed by developers who want to create
    their own argument parser with custom fields and behavior.
    """

    arguments_dict: dict[str, ArgParseItem] = {}
    children: dict[str, type] = {}  # Dictionary of subcommand name to subcommand class
    inject_as_subparser: bool = True


    meta__name: str = NOT_SET

    def __init__(
        self,
        description: str = None,
        add_help: bool = True,
        parent: "Parser" = None,
        name: str = None,
        key: str = None,
        parser: argparse.ArgumentParser = None,
        inject_as_subparser: bool = True,
        proc_name: str = None,
    ):



        super().__init__(parent=parent)

        self.name = self.query_cfg_parents("name", default=self.__class__.__name__)
        self.key = key
        self.fkey = self.get_fname(attr="key")
        self.inject_as_subparser = inject_as_subparser
        self.proc_name = proc_name

        # Add children link
        self.children = {}
        self.registry = {}
        if parent:
            parent.children[self.key] = self
            self.registry = parent.registry
        self.registry[self.fkey] = self #RegistryEntry(config=self)

        if parser is None:
            usage = self.query_cfg_parents("help_usage", default=None)      
            desc = self.query_cfg_parents("help_description", default=self.__doc__)
            epilog = self.query_cfg_parents("help_epilog", default=None)

            fenv = FormatEnv({"self": self})
            usage = prepare_docstring(usage, variables=fenv.get())
            desc = prepare_docstring(desc, variables=fenv.get())
            epilog = prepare_docstring(epilog, variables=fenv.get())
            self.parser = argparse.ArgumentParser(
                prog=self.proc_name,
                usage=usage,
                description=desc,
                epilog=epilog,
                formatter_class=RecursiveHelpFormatter,
                add_help=add_help,
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

    def __getitem__(self, key):
        return self.children[key]


    @property
    def subparsers(self):
        """Lazily create and return the subparsers object."""
        # if not self.inject_as_subparser:
        #     return self.parser

        if self._subparsers is None:
            level = len(self.get_hierarchy())
            self._subparsers = self.parser.add_subparsers(
                dest=f"__cli_cmd__{level}", 
                help="Available commands"
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

        # Add __cli_self__ argument
        arguments["__cli_self__"] = Argument(help=argparse.SUPPRESS, default=self)

        # Create all options
        for key, arg in arguments.items():
            arg.create_arg(key, self)

    def init_subcommands(self):
        """Add all parsers defined in the children dictionary."""
        children_dict = self.children or {}

        # Add arguments from class attributes that are Command instances
        for cls in self.__class__.__mro__:
            for attr_name, attr_value in cls.__dict__.items():
                if isinstance(attr_value, Command):
                    # Store the attribute name as the key in the Fn instance
                    attr_value.destination = attr_name
                    children_dict[attr_name] = attr_value

        for key, arg in children_dict.items():
            arg.create_subcommand(key, self)



    def show_help(self):
        self.parser.print_help()
    def show_usage(self):
        self.parser.print_usage()
    def show_epilog(self):
        self.parser.print_epilog()

    def cli_exit(self, status=0, message=None):
        "Exit application"
        self.parser.exit(status=status, message=message)

    def cli_exit_error(self, message):
        "Exit application with error message"
        self.parser.error(message)

    def cli_run(self, ctx, **kwargs):
        "Placeholder for cli_run"

        # pprint(ctx)


        # Check if class is a leaf or not
        if len(ctx.cli_children) > 0:
            self.show_help()
        else:
            # print(f"No code to execute, method is missing: {self.__class__.__name__}.cli_run(self, ctx, **kwargs)")
            raise exception.ClakNotImplementedError(f"No 'cli_run' method found for {self}")


    def cli_group(self, ctx, **kwargs):
        "Placeholder for cli_group"


    def find_closest_subcommand(self, args=None):
        "Find the closest subcommand from CLI args"

        # Get the current command line from sys.argv
        current_cmd = sys.argv[1:] if args is None else args
        last_child = self

        # Loop through each argument to find the deepest valid subcommand
        for arg in current_cmd:
            # Skip options (starting with -)
            if arg.startswith('-'):
                break
                
            # Check if argument exists as a subcommand
            if arg in last_child.children:
                last_child = last_child.children[arg]
            else:
                break

        return last_child


    def clean_terminate(self, err, known_exceptions=None):
        "Terminate nicely the program depending the exception"

        def default_exception_handler(self, exception):
            print(f"Default exception handler: {exception}")
            sys.exit(1)

        # Prepare known exceptions list
        known_exceptions = known_exceptions or []
        known_exceptions_conf = {}
        for _exception in known_exceptions:
            exception_fn = default_exception_handler
            if isinstance(_exception, Sequence):
                exception_cls = _exception[0]
                if len(_exception) > 1:
                    exception_fn = _exception[1]
            else:
                exception_cls = _exception

            exception_name = str(exception_cls)
            known_exceptions_conf[exception_name] = {
                "fn": exception_fn,
                "exception": exception_cls,
            }
        known_exceptions_list = tuple([val["exception"] for val in known_exceptions_conf.values()])

        # Check user overrides
        if known_exceptions_list and isinstance(err, known_exceptions_list):
            get_handler = known_exceptions_conf[str(type(err))]["fn"]
            get_handler(self,err)
            # If handler did not exited, ensure we do
            sys.exit(1)

        # If user made an error on command line, show usage before leaving
        if isinstance(err, exception.ClakParseError):
            # Must go to stdout
            self.show_usage()
            print(f"{err}")
            sys.exit(err.rc)

        # Choose dead end way generic user error
        if isinstance(err, exception.ClakUserError):
            if isinstance(err.advice, str):
                logger.warning(err.advice)

            print(f"{err}")
            sys.exit(err.rc)

        # Internal clak errors
        if isinstance(err, exception.ClakError):
            err_name = err.__class__.__name__
            if isinstance(err.advice, str):
                logger.warning(err.advice)

            err_message = err.message
            if not err_message:
                err_message = err.__doc__

            # logger.error(err)
            print(f"{err}")
            logger.critical(f"Program exited with bug {err_name}({err.rc}): {err_message}")
            sys.exit(err.rc)

        # if isinstance(err, yaml.scanner.ScannerError):
        #     log.critical(err)
        #     log.critical("Paasify exited with: YAML Scanner error (file syntax)")
        #     sys.exit(error.YAMLError.rc)

        # if isinstance(err, yaml.composer.ComposerError):
        #     log.critical(err)
        #     log.critical("Paasify exited with: YAML Composer error (file syntax)")
        #     sys.exit(error.YAMLError.rc)

        # if isinstance(err, yaml.parser.ParserError):
        #     log.critical(err)
        #     log.critical("Paasify exited with: YAML Parser error (file format)")
        #     sys.exit(error.YAMLError.rc)

        # if isinstance(err, sh.ErrorReturnCode):
        #     log.critical(err)
        #     log.critical(
        #         f"Paasify exited with: failed command returned {err.exit_code}")
        #     sys.exit(error.ShellCommandFailed.rc)

        oserrors = [
            PermissionError,
            FileExistsError,
            FileNotFoundError,
            InterruptedError,
            IsADirectoryError,
            NotADirectoryError,
            TimeoutError,
        ]

        if err.__class__ in oserrors:

            # Decode OS errors
            # errno = os.strerror(err.errno)
            # errint = str(err.errno)

            logger.critical(f"Program exited with OS error: {err}")
            sys.exit(err.errno)

    def parse_args(self, args=None):
        parser = self.parser
        argcomplete.autocomplete(parser)

        # args = args[0] if len(args) > 0 else sys.argv[1:]

        if args is None:
            args = sys.argv[1:]
        elif isinstance(args, str):
            args = args.split(" ")
        elif isinstance(args, list):
            args = args
        elif isinstance(args, dict):
            return args
        else:
            raise ValueError(f"Invalid args type: {type(args)}")

        return parser.parse_args(args)
    

    def dispatch(self, args=None, exit=None, debug=None):
        "Main dispatch function, must correctly handle exit status and exceptions and so"
        # It must correctly handle exit status and exceptions.

        try:
            return self.cli_execute(args=args)
        except Exception as err:
            error = err
            debug = debug if isinstance(debug, bool) else CLAK_DEBUG

            # Always show traceback if debug mode is enabled
            if debug is True:
                logger.error(traceback.format_exc())

            known_exceptions = self.query_cfg_parents("known_exceptions", default=[])      

            self.clean_terminate(error, known_exceptions)

            # Developper catchall
            if debug is False:
                logger.error(traceback.format_exc())
            logger.critical(f"Uncatched error {err.__class__}; this may be a bug!")
            logger.critical("Exit 1 with bugs")
            sys.exit(1)


    def cli_execute(self, args=None):
        "Main dispatch function"


        try:
            args = self.parse_args(args)
        except argparse.ArgumentError as err:
            msg = f"Could not parse command line: {err.argument_name} {err.message}"
            # print(f"Error: {msg}")
            raise exception.ClakParseError(msg) from err

        # Prepare args and context
        hook_list = {}
        
        args = args.__dict__
        cli_command_hier = [value for key, value in sorted(args.items()) if key.startswith("__cli_cmd__")]
        args = {key: value for key, value in args.items() if not key.startswith("__cli_cmd__")}
        cli_self = args.pop("__cli_self__")

        # Prepare data
        fn_group_name = "cli_group"
        fn_exec_name = "cli_run"
        fn_hook_prefix = "cli_hook__"
        name = self.name
        hierarchy = cli_self.get_hierarchy()
        node_count = len(hierarchy)

        logger.debug("Run instance %s", cli_self)

        ctx = {}
        ctx["registry"] = self.registry

        # Fetch settings
        ctx["name"] = name
        ctx["app_name"] = self.query_cfg_parents("app_name", default=name)
        ctx["app_proc_name"] = self.query_cfg_parents("app_proc_name", default=self.proc_name)
        ctx["app_env_prefix"] = self.query_cfg_parents("app_env_prefix", default=name.upper())
        
        # Loop constant
        ctx["cli_self"] = cli_self
        ctx["cli_root"] = self
        ctx["cli_depth"] = node_count
        ctx["cli_commands"] = cli_command_hier
        ctx["args"] = SimpleNamespace(**args)

        # Shared data
        ctx["data"] = {}
        ctx["plugins"] = {}

        # Loop var init
        ctx["cli_first"] = True
        ctx["cli_state"] = None
        ctx["cli_methods"] = None

        # Execute all nodes in hierarchy
        for idx, node in enumerate(hierarchy):
            last_node = True if idx == node_count - 1 else False
            has_children = node._subparsers is not None

            logger.info(f"Processing node {idx}:{node}.{fn_group_name}")
            # print(f"Node {idx}:{node}")

            # Prepare hooks list
            cls_hooks = [ method for method in dir(self) if method.startswith(fn_hook_prefix)]
            for hook_name in cls_hooks:
                if not hook_name in hook_list:
                    hook_fn = getattr(self, hook_name, None)
                    if hook_fn is not None:
                        # Hooks order should be preserved with dict
                        hook_list[hook_name] = hook_fn


            # Update ctx with node attributes
            ctx["cli_parent"] = hierarchy[-2] if len(hierarchy) > 1 else None
            ctx["cli_parents"] = hierarchy[:idx]
            ctx["cli_children"] = dict(node.children)
            ctx["cli_last"] = last_node
            ctx["cli_hooks"] = hook_list
            ctx["cli_index"] = idx
            

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

            # Store the list of available plugins methods
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
                run_fn(ctx=_ctx, **_ctx.args.__dict__)
            
            # Change status
            ctx["cli_first"] = False

# # # Compatibility
# ArgumentParser = Parser
# ArgumentParserPlus = Parser
# ArgParser = Parser
Command = SubParser
# SubCommand = SubParser

# # Argparse mode
# ArgumentParser()
# Argument()
# SubParser()

# # Clak mode:
# ClakParser()
# Opt()
# Arg()
# Cmd()
