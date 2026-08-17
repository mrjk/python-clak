"""Clak parser: ParserNode build, dispatch, and execute.

Descriptors (Argument, Arg, Opt, SubParser, MetaSetting, docstring helpers)
live in ``clak.core.descriptors`` and are re-exported here for compatibility.

Canonical public names: ``Parser``, ``Argument``, ``Command`` (alias of SubParser).
Optional helpers: ``Arg`` (positionals), ``Opt`` (flags).
Instantiate a root ``Parser`` to parse and run; it calls ``dispatch()`` automatically
unless ``parse=False``.
"""

import logging
import os
import shlex
import sys
import traceback
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Union

from clak import exception
from clak.common import ObjectNamespace
from clak.core.argparse_ import (
    HELP_SUBCOMMANDS_ALL,
    ArgumentParserPlus,
    HelpLayout,
    argparse,
    format_argument_error,
)
from clak.core.descriptors import (  # pylint: disable=unused-import
    Arg,
    ArgParseItem,
    Argument,
    FormatEnv,
    MetaSetting,
    Opt,
    SubParser,
    prepare_docstring,
)
from clak.core.nodes import NOT_SET, Node
from clak.runtime.facts import detect_facts
from clak.runtime.runtime import detect_runtime
from clak.runtime.settings import CLAK_DEBUG
from clak.views import ClakView
from clak.views.base import merge_view_settings

logger = logging.getLogger(__name__)


def _exit_broken_pipe(rc=1):
    """Exit quietly after BrokenPipeError (e.g. ``| head`` / ``| tail``).

    Redirects stdout to ``/dev/null`` so Python's shutdown flush does not print
    ``Exception ignored ... BrokenPipeError``.
    """
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except Exception:  # pylint: disable=broad-exception-caught
        try:
            sys.stdout.close()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
    sys.exit(rc)


# Backwards-compatible aliases (preferred public name is Command via clak.__init__)
Command = SubParser

PROPAGATE_OPTIONS_GROUP_DEFAULT = "parent options"


def _flag_propagates(arg: Argument) -> bool:
    """True when this flag should be copied onto descendant parsers."""
    return bool(arg.kwargs.get("propagate", True))


def _suppress_attach_overrides(arg: Argument, extra: Optional[dict] = None) -> dict:
    """Attach-time overrides so a copy does not overwrite an outer dest.

    Do not set required unless the source flag is required: some argparse
    actions reject the required= keyword.
    """
    overrides = {"default": argparse.SUPPRESS}
    if arg.kwargs.get("required"):
        overrides["required"] = False
    if extra:
        overrides.update(extra)
    return overrides


def _argument_flag_strings(arg: Argument, dest: str) -> tuple[str, ...]:
    """Option strings for a flag Argument, or empty if it is positional."""
    if dest.startswith("__"):
        return ()
    if arg.args:
        if str(arg.args[0]).startswith("-"):
            return tuple(str(name) for name in arg.args)
        return ()
    if not dest:
        return ()
    if len(dest) <= 2:
        return (f"-{dest}",)
    return (f"--{dest}",)


# Main parser object


class ParserNode(Node):  # pylint: disable=too-many-instance-attributes
    """An extensible argument parser that can be inherited to create custom CLIs.

    This class provides a framework for building complex command-line interfaces with:
    - Hierarchical subcommands
    - Automatic help generation
    - Plugin support
    - Custom argument types
    - Exception handling

    The parser can be extended by:
    1. Subclassing and adding Argument instances as class attributes
    2. Adding SubParser instances to create command hierarchies
    3. Implementing cli_run() for command execution
    4. Implementing cli_group() for command group behavior

    Attributes:
        arguments_dict (dict): Dictionary of argument name to ArgParseItem
        children (dict): Dictionary of subcommand name to subcommand class
        meta__name (str): ParserNode name
    """

    arguments_dict: dict[str, ArgParseItem] = {}
    children: dict[str, type] = {}  # Dictionary of subcommand name to subcommand class

    meta__name: str = NOT_SET

    meta__subcommands_dict: dict[str, SubParser] = {}
    meta__arguments_dict: dict[str, Argument] = {}

    meta__cli_view: ClakView = None

    # Meta settings
    meta__config__name = MetaSetting(
        help="Name of the parser",
    )
    meta__config__app_name = MetaSetting(
        help="Name of the application",
    )
    meta__config__app_proc_name = MetaSetting(
        help="Name of the application processus",
    )
    meta__config__help_usage = MetaSetting(
        help="Message to display in help usage",
    )
    meta__config__help_description = MetaSetting(
        help="Message to display in help description",
    )
    meta__config__help_epilog = MetaSetting(
        help="Message to display in help epilog",
    )
    meta__config__help_formatter = MetaSetting(
        help="argparse HelpFormatter class for --help",
    )
    meta__config__help_subcommands = MetaSetting(
        help=(
            "How --help lists subcommands: 'all' (nested children, default) "
            "or 'top' (immediate children only). Inherited; a child may override."
        ),
    )
    meta__config__help_hide_parent = MetaSetting(
        help=(
            "When listing nested subcommands, replace the parent path with "
            "spaces so only the leaf name is shown (default True)."
        ),
    )
    meta__config__command_groups = MetaSetting(
        help=(
            "Ordered (key, title) pairs for subcommand help sections. "
            "Formatter metadata only; not a second add_subparsers."
        ),
    )
    meta__config__parse_intermixed = MetaSetting(
        help=(
            "Mix this command's flags and positionals (default True). "
            "Inherited; set False for argparse leftover errors after a flag. "
            "No-op on parsers with subcommands or nargs=REMAINDER."
        ),
    )
    meta__config__propagate_options = MetaSetting(
        help=(
            "Copy eligible ancestor flags onto this parser (default True). "
            "Inherited; a child may set False. Per-flag opt-out: propagate=False."
        ),
    )
    meta__config__propagate_options_group = MetaSetting(
        help=(
            "Help section title for propagated ancestor flags "
            "(default 'parent options'). Inherited; a child may override."
        ),
    )
    meta__config__known_exceptions = MetaSetting(
        help="List of known exceptions to handle",
    )
    meta__config__exception_handlers = MetaSetting(
        help=(
            "Extra (exception_type, handler) pairs or handler callables "
            "for clean_terminate (third-party libs, etc.)"
        ),
    )

    # Views support
    meta__config__cli_view = MetaSetting(
        help="class of the view to use",
    )
    meta__config__runtime_narrow_width = MetaSetting(
        help="Column threshold for ctx.runtime.is_narrow (default 80)",
    )

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        add_help: bool = True,
        parent: "ParserNode" = None,
        name: str = None,
        key: str = None,
        parser: argparse.ArgumentParser = None,
        proc_name: str = None,
    ):
        """Initialize the parser.

        Args:
            add_help (bool): Whether to add help flags
            parent (ParserNode): Parent parser instance
            name (str): ParserNode name
            key (str): ParserNode key
            parser (ArgumentParser): Existing parser to use
            proc_name (str): Process name
        """
        self.logger = logger

        super().__init__(parent=parent)

        self.name = self.query_cfg_parents("name", default=self.__class__.__name__)
        self.key = key
        self.fkey = self.get_fname(attr="key")
        self.proc_name = proc_name
        self.add_help = add_help

        # Add children link
        self.children = {}
        self.registry = {}
        if parent:
            parent.children[self.key] = self
            self.registry = parent.registry
        self.registry[self.fkey] = self

        # Create or reuse parent parser
        if parser is None:
            self.parser = self.create_parser()
            self.proc_name = self.parser.prog
        else:
            self.parser = parser
            self.proc_name = self.parent.proc_name
            # add_parser() builds ArgumentParserPlus without clak_instance.
            if hasattr(self.parser, "clak_instance"):
                self.parser.clak_instance = self

        # Init _subparsers
        self._subparsers = None
        self.local_flag_arguments: dict[str, Argument] = {}

        # Add arguments and subcommands
        # meta__arguments_dict = {}
        # meta__subcommands_dict = {}
        self.add_arguments()
        self.add_subcommands()

    def __repr__(self):
        return f"<{self.__class__.__module__}.{self.__class__.__name__}>"

    def create_parser(self):
        "Create a new parser"
        usage = self.query_cfg_parents("help_usage", default=None)
        desc = self.query_cfg_parents("help_description", default=self.__doc__)
        epilog = self.query_cfg_parents("help_epilog", default=None)

        fenv = FormatEnv({"self": self})
        usage = prepare_docstring(usage, variables=fenv.get())
        desc = prepare_docstring(desc, variables=fenv.get())
        epilog = prepare_docstring(epilog, variables=fenv.get())
        parser = ArgumentParserPlus(
            prog=self.proc_name,
            usage=usage,
            description=desc,
            epilog=epilog,
            formatter_class=self.get_help_formatter_class(),
            add_help=self.add_help,
            exit_on_error=False,
            clak_instance=self,
        )
        return parser

    def get_help_formatter_class(self):
        """Return the argparse HelpFormatter class for this node.

        Mixins set ``meta__help_formatter`` (or ``Meta.help_formatter``).
        Unset walks parents, then ``RichRecursiveHelpFormatter``.
        Opt out with ``Meta.help_formatter = RecursiveHelpFormatter``.
        """
        from clak.comp.help import (  # pylint: disable=import-outside-toplevel
            RichRecursiveHelpFormatter,
        )

        return self.query_cfg_parents(
            "help_formatter",
            default=RichRecursiveHelpFormatter,
            include_self=True,
        )

    def __getitem__(self, key):
        return self.children[key]

    def get_fname(self, attr="key"):
        "Get full name of the parser, use key instead of name by default"
        return super().get_fname(attr=attr)

    @property
    def subparsers(self):
        """Lazily create and return the subparsers object."""
        if self._subparsers is None:
            level = len(self.get_hierarchy())
            self._subparsers = self.parser.add_subparsers(
                dest=f"__cli_cmd__{level}",
                help="Available commands",
                parser_class=ArgumentParserPlus,
            )
            command_groups = self.query_cfg_inst("command_groups", default=())
            help_subcommands = self.query_cfg_parents(
                "help_subcommands",
                default=HELP_SUBCOMMANDS_ALL,
                include_self=True,
            )
            help_hide_parent = self.query_cfg_parents(
                "help_hide_parent",
                default=True,
                include_self=True,
            )
            # pylint: disable=protected-access
            self._subparsers._clak_help = HelpLayout(
                subcommands=help_subcommands,
                hide_parent=help_hide_parent,
                command_groups=tuple(command_groups),
            )
        return self._subparsers

    # Argument management
    # ========================

    def _skip_argument_names(self) -> set:
        """Names of class Argument attrs to omit (view mixins override)."""
        return set()

    def _prepare_argument(  # pylint: disable=unused-argument
        self, key: str, arg: Argument
    ) -> Argument:
        """Hook to adjust an argument before attach (view mixins override)."""
        return arg

    def add_arguments(self, arguments: dict = None):
        """Initialize all argument options defined for this parser.

        This method:
        1. Collects arguments from arguments_dict
        2. Collects arguments defined as class attributes
        3. Adds internal arguments like __cli_self__
        4. Creates all argument parser entries
        5. Copies ancestor flags onto this parser when inherit is on
        """
        if arguments is None:
            arguments = getattr(self, "meta__arguments_dict", None)
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise TypeError(f"Got {type(arguments)} instead of dict")
        arguments = dict(arguments)

        skip = self._skip_argument_names()

        # Add arguments from class attributes including inherited ones
        for cls in self.__class__.__mro__:
            for name, value in vars(cls).items():
                if isinstance(value, Argument) and name not in arguments:
                    if name in skip:
                        continue
                    value.destination = name
                    arguments[name] = value

        # Add __cli_self__ argument
        arguments["__cli_self__"] = Argument(help=argparse.SUPPRESS, default=self)

        ancestor_dests, ancestor_strings = self._ancestor_flag_index()
        local_flags: dict[str, Argument] = {}

        for key, arg in arguments.items():
            arg = self._prepare_argument(key, arg)
            overrides = None
            flag_strings = _argument_flag_strings(arg, key)
            if flag_strings:
                local_flags[key] = arg
                if key in ancestor_dests or (ancestor_strings & set(flag_strings)):
                    overrides = _suppress_attach_overrides(arg)
            self.add_argument(key, arg, attach_overrides=overrides)

        self.local_flag_arguments = local_flags

        if self.query_cfg_parents("propagate_options", default=True, include_self=True):
            self._attach_inherited_parent_flags(arguments, local_flags)

    def _ancestor_flag_index(self) -> tuple[set[str], set[str]]:
        """Dests and option strings from ancestors' locally defined flags."""
        dests: set[str] = set()
        strings: set[str] = set()
        node = self.parent
        while node:
            for dest, arg in node.local_flag_arguments.items():
                dests.add(dest)
                strings.update(_argument_flag_strings(arg, dest))
            node = node.parent
        return dests, strings

    def _attach_inherited_parent_flags(
        self, arguments: dict, local_flags: dict[str, Argument]
    ) -> None:
        """Copy closest ancestor flags onto this parser (default=SUPPRESS)."""
        seen_dests = set(arguments)
        seen_strings: set[str] = set()
        for dest, arg in local_flags.items():
            seen_strings.update(_argument_flag_strings(arg, dest))

        group = self.query_cfg_parents(
            "propagate_options_group",
            default=PROPAGATE_OPTIONS_GROUP_DEFAULT,
            include_self=True,
        )
        group_extra = {
            "option_group": group,
            "argument_group": None,
        }

        node = self.parent
        while node:
            for dest, arg in node.local_flag_arguments.items():
                if dest in seen_dests:
                    continue
                if not _flag_propagates(arg):
                    continue
                strings = _argument_flag_strings(arg, dest)
                if not strings or (seen_strings & set(strings)):
                    continue
                self.add_argument(
                    dest,
                    arg,
                    attach_overrides=_suppress_attach_overrides(arg, extra=group_extra),
                )
                seen_dests.add(dest)
                seen_strings.update(strings)
            node = node.parent

    def add_argument(
        self,
        key: str,
        arg: Optional[Argument] = None,
        attach_overrides: Optional[dict] = None,
        **kwargs: Any,
    ) -> None:
        """Add an argument to this parser.

        Args:
            key (str): The key/name for the argument
            arg (Argument): The argument object to add
            attach_overrides (dict): Kwargs applied only to this attach
            **kwargs (Any): Additional keyword arguments to pass to add_argument()

        This method adds a new argument to the parser. The argument can be either a
        positional argument or an optional flag, determined by the Argument object.
        """

        if arg is None:
            arg = Argument(**kwargs)

        arg.attach_arg_to_parser(key, self, attach_overrides=attach_overrides)

    # Subcommand management
    # ========================

    def add_subcommands(self, subcommands: dict = None):
        """Initialize all subcommands defined for this parser.

        This method:
        1. Collects subcommands from children dictionary
        2. Collects Command instances defined as class attributes
        3. Creates parser entries for all subcommands
        """

        if subcommands is None:
            subcommands = getattr(self, "meta__subcommands_dict", None)
        if subcommands is None:
            subcommands = {}
        if not isinstance(subcommands, dict):
            raise TypeError(f"Got {type(subcommands)} instead of dict")
        subcommands = dict(subcommands)

        # Collect Command instances from class attributes (child wins)
        for cls in self.__class__.__mro__:
            for attr_name, attr_value in cls.__dict__.items():
                if isinstance(attr_value, Command) and attr_name not in subcommands:
                    attr_value.destination = attr_name
                    subcommands[attr_name] = attr_value

        for key, arg in subcommands.items():
            # arg.attach_sub_to_parser(key, self)
            self.add_subcommand(key, arg)

    def add_subcommand(self, key: str, arg=None, **kwargs) -> None:
        "Add a subcommand to this parser"
        if arg is None:
            arg = Command(**kwargs)

        arg.attach_sub_to_parser(key, self)

    # Help methods
    # ========================

    def show_help(self):
        """Display the help message for this parser."""
        self.parser.print_help()

    def show_usage(self):
        """Display the usage message for this parser."""
        self.parser.print_usage()

    def show_epilog(self):
        """Display the epilog message for this parser."""
        self.parser.print_epilog()

    # Execution helpers
    # ========================

    def cli_exit(self, status=0, message=None):
        """Exit the CLI application with given status and message.

        Args:
            status (int): Exit status code
            message (str): Optional message to display
        """
        self.parser.exit(status=status, message=message)

    def cli_exit_error(self, message):
        """Exit the CLI application with an error message.

        Args:
            message (str): Error message to display
        """
        self.parser.error(message)

    def cli_run(self, **kwargs: Any) -> None:  # pylint: disable=unused-argument
        """Execute the command implementation.

        This method should be overridden by subclasses to implement command behavior.
        The base implementation shows help for non-leaf nodes.

        Args:
            **kwargs: Additional keyword arguments from command line

        Raises:
            ClakNotImplementedError: If leaf node has no implementation
        """

        ctx = kwargs["ctx"]

        # Check if class is a leaf or not
        if len(ctx.cli_children) > 0:
            self.show_help()
        else:
            raise exception.ClakNotImplementedError(
                f"No 'cli_run' method found for {self}"
            )

    def cli_group(self, ctx: SimpleNamespace, **_: Any) -> None:
        """Execute group-level command behavior.

        Args:
            ctx: Command context object
            **_: Unused keyword arguments
        """

    @staticmethod
    def _exception_exit_code(err, default=1):
        rc = getattr(err, "rc", default)
        return rc if isinstance(rc, int) else default

    @staticmethod
    def _exception_advice(err):
        advice = getattr(err, "advice", None)
        if isinstance(advice, str):
            logger.warning(advice)

    def _terminate_app_exception(self, err):
        """Default handler for app exceptions (Paasify-style: rc + message)."""
        self._exception_advice(err)
        print(err, file=sys.stderr)
        rc = self._exception_exit_code(err)
        logger.critical(
            "Program exited with: error %s: %s",
            rc,
            err.__class__.__name__,
        )
        sys.exit(rc)

    @staticmethod
    def _iter_exception_entries(entries):
        for entry in entries or []:
            if isinstance(entry, (tuple, list)) and entry:
                exc_type = entry[0]
                handler = entry[1] if len(entry) > 1 else None
                yield exc_type, handler
            else:
                yield entry, None

    def _run_exception_handler(self, handler, err):
        if handler is None:
            self._terminate_app_exception(err)
            return
        result = handler(self, err)
        if isinstance(result, int):
            sys.exit(result)
        sys.exit(self._exception_exit_code(err))

    def clean_terminate(self, err, known_exceptions=None):
        """Handle program termination based on exception type.

        Processing order (Paasify-style chain):

        1. ``Meta.known_exceptions`` on the root parser (class or ``(class, handler)``)
        2. ``Meta.exception_handlers`` (third-party libs: YAML, shell, …)
        3. Built-in Clak exceptions
        4. Broken pipe (``| head`` / ``| tail``) - quiet exit
        5. Common OS errors

        If nothing matches, return and let ``dispatch()`` report an unexpected bug.

        Args:
            err (Exception): The exception that triggered termination
            known_exceptions (list): List of exception types to handle specially
        """

        # 1. App-known exceptions (e.g. PaasifyError hierarchy)
        for exc_type, handler in self._iter_exception_entries(known_exceptions):
            if isinstance(err, exc_type):
                self._run_exception_handler(handler, err)

        # 2. Registered third-party / library handlers
        extra_handlers = self.query_cfg_parents("exception_handlers", default=[])
        for exc_type, handler in self._iter_exception_entries(extra_handlers):
            if isinstance(err, exc_type):
                self._run_exception_handler(handler, err)

        # 3. Clak parse errors — show usage first (leaf parser when known)
        if isinstance(err, exception.ClakParseError):
            if err.parser is not None:
                err.parser.print_usage()
            else:
                self.show_usage()
            print(f"{err}", file=sys.stderr)
            sys.exit(err.rc)

        # 4. User-facing Clak errors
        if isinstance(err, exception.ClakUserError):
            self._exception_advice(err)
            print(f"{err}", file=sys.stderr)
            sys.exit(err.rc)

        # 5. Other Clak errors (app / bug)
        if isinstance(err, exception.ClakError):
            err_name = err.__class__.__name__
            self._exception_advice(err)
            err_message = err.message or err.__doc__
            print(f"{err}", file=sys.stderr)
            logger.critical(
                "Program exited with bug %s(%s): %s",
                err_name,
                err.rc,
                err_message,
            )
            sys.exit(err.rc)

        # 6. Broken pipe from | head / | tail - quiet exit (no bug log)
        if isinstance(err, BrokenPipeError):
            _exit_broken_pipe()

        # 7. OS errors (BrokenPipeError already handled above)
        if isinstance(err, OSError):
            logger.critical("Program exited with OS error: %s", err)
            sys.exit(err.errno if err.errno is not None else 1)

    def parse_args(
        self, args: Optional[Union[str, List[str], Dict[str, Any]]] = None
    ) -> argparse.Namespace:
        """Parse command line arguments.

        Args:
            args: Arguments to parse, can be:
                - None: Use sys.argv[1:]
                - str: Shell-style split via ``shlex.split``
                - list: Use directly
                - dict: Return as-is

        Returns:
            Namespace: Parsed argument namespace

        Raises:
            ValueError: If args is invalid type
        """
        parser = self.parser
        # argcomplete.autocomplete(parser)

        # args = args[0] if len(args) > 0 else sys.argv[1:]

        if args is None:
            args = sys.argv[1:]
        elif isinstance(args, str):
            args = shlex.split(args)
        elif isinstance(args, list):
            pass
        elif isinstance(args, dict):
            return args
        else:
            raise ValueError(f"Invalid args type: {type(args)}")

        return parser.parse_args(args)

    def dispatch(  # pylint: disable=too-many-branches
        self,
        args: Optional[Union[str, List[str], Dict[str, Any]]] = None,
        trace: bool = False,
        **_: Any,
    ) -> Any:
        """Main dispatch function for command execution.

        Args:
            args: Arguments to parse
            **_: Unused keyword arguments
        """

        # Process or reuse args
        # if args is None:
        error = None
        try:
            args = self.parse_args(args)
            args = args.__dict__
        except argparse.ArgumentError as err:
            error = exception.ClakParseError(
                format_argument_error(err),
                parser=getattr(err, "clak_parser", None),
            )
            # raise exception.ClakParseError(msg) from err

        if not error:
            if not isinstance(args, dict):
                raise TypeError(
                    f"Parsed args must be a dict, got {type(args).__name__}"
                )

            # Check for trace mode
            if "app_trace_mode" in args:
                trace = args["app_trace_mode"]
            if CLAK_DEBUG:
                trace = True

            # Leaf command (may carry Meta.cli_view / view mixins on nested cmds)
            cli_leaf = args.get("__cli_self__", self)

            # Run app command + view render (pipe breaks during print hit clean_terminate)
            try:
                data = self.cli_execute(args=args)

                # Prepare viewer output (CLI view mixins may stash settings on root)
                view_settings = getattr(self, "_clak_view_settings", None) or {}
                if isinstance(data, ClakView):
                    render_kwargs = merge_view_settings(
                        getattr(data, "settings", None), view_settings
                    )
                    data.render(**render_kwargs)
                else:
                    viewer = cli_leaf.query_cfg_parents("cli_view", default=None)
                    if isinstance(viewer, type) and issubclass(viewer, ClakView):
                        viewer = viewer()
                    if viewer is not None:
                        if not isinstance(viewer, ClakView):
                            raise TypeError(
                                "Meta.cli_view must be a ClakView instance or subclass"
                            )
                        viewer.render(data, **view_settings)

                return data

            except Exception as err:  # pylint: disable=broad-exception-caught
                error = err

        if trace is True:
            logger.error("".join(traceback.format_exception(error)))

        # Process exception handling
        known_exceptions = self.query_cfg_parents("known_exceptions", default=[])
        self.clean_terminate(error, known_exceptions)

        # Developer catchall — unexpected bug (Paasify-style)
        if trace is False:
            logger.error("".join(traceback.format_exception(error)))
        logger.critical(
            "Uncaught error %s; this may be a bug! Please report to the developer.",
            error.__class__.__name__,
        )
        logger.critical("Error: %s", error)
        sys.exit(1)

    def cli_execute(  # pylint: disable=too-many-locals,too-many-statements
        self, args: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute the command with given arguments.

        Args:
            args: Arguments to parse

        Raises:
            ClakParseError: If argument parsing fails
            NotImplementedError: If command has no implementation
        """
        if not isinstance(args, dict):
            raise TypeError(
                f"cli_execute args must be a dict, got {type(args).__name__}"
            )

        # Prepare args and context
        hook_list = {}

        # args = args.__dict__
        cli_command_hier = [
            value
            for key, value in sorted(args.items())
            if key.startswith("__cli_cmd__")
        ]
        args = {
            key: value
            for key, value in args.items()
            if not key.startswith("__cli_cmd__")
        }

        cli_self = self
        if "__cli_self__" in args:
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
        ctx["app_proc_name"] = self.query_cfg_parents(
            "app_proc_name", default=self.proc_name
        )
        # ctx["app_env_prefix"] = self.query_cfg_parents(
        #     "app_env_prefix", default=name.upper()
        # )

        # Loop constant
        ctx["cli_self"] = cli_self
        ctx["cli_root"] = self
        ctx["cli_depth"] = node_count
        ctx["cli_commands"] = cli_command_hier
        ctx["args"] = ObjectNamespace(**args)

        # Shared data
        ctx["data"] = {}
        ctx["plugins"] = {}

        narrow_width = self.query_cfg_parents("runtime_narrow_width", default=None)
        ctx["runtime"] = detect_runtime(narrow_width=narrow_width)
        ctx["facts"] = detect_facts()

        # Loop var init
        ctx["cli_first"] = True
        ctx["cli_state"] = None
        ctx["cli_methods"] = None

        # Execute all nodes in hierarchy
        ret = None
        # pylint: disable=attribute-defined-outside-init
        for idx, node in enumerate(hierarchy):
            last_node = idx == (node_count - 1)

            logger.info("Processing node %d:%s.%s", idx, node, fn_group_name)

            # Prepare hooks list (per hierarchy node — mixins on subcommands)
            cls_hooks = [
                method for method in dir(node) if method.startswith(fn_hook_prefix)
            ]
            for hook_name in cls_hooks:
                hook_fn = getattr(node, hook_name, None)
                if hook_fn is not None:
                    # Last node with this name wins (leaf mixin rebinds root)
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
            _ctx = ObjectNamespace(**sorted_ctx)
            _ctx.cli_state = "run_hooks"

            # Process hooks
            for name, hook_fn in hook_list.items():
                # hook_fn = getattr(self, hook, None)
                # if hook_fn is not None:
                logger.info("Run hook %d:%s.%s", idx, node, name)
                hook_fn(node, _ctx)

            # Store the list of available plugins methods
            _ctx.cli_methods = getattr(node, "cli_methods", {})

            # Run group_run
            _ctx.cli_state = "run_groups"

            group_fn = getattr(node, fn_group_name, None)
            # print ("GROUP FN", group_fn)
            if group_fn is not None:
                logger.info(
                    "Group function execute: %d:%s.%s", idx, node, fn_group_name
                )
                group_fn(ctx=_ctx, **_ctx.__dict__)

            # Run leaf only if last node
            _ctx.cli_state = "run_exec"
            if last_node is True:
                run_fn = getattr(node, fn_exec_name, None)

                logger.info("Run function execute: %d:%s.%s", idx, node, fn_exec_name)
                ret = run_fn(ctx=_ctx, **_ctx.args.__dict__)

            # Change status
            ctx["cli_first"] = False

        return ret


class Parser(ParserNode):
    """A simplified parser class that extends ParserNode.

    This class provides a more streamlined interface to ParserNode by:
    - Automatically parsing arguments on initialization
    - Maintaining compatibility with legacy argument parser names
    - Providing simpler command/argument creation methods

    Args:
        *args: Positional arguments passed to ParserNode
        parse (bool): Whether to automatically parse arguments on init,
            only on root nodes
        **kwargs: Keyword arguments passed to ParserNode
    """

    def __init__(self, *args: Any, parse: bool = True, **kwargs: Any):
        super().__init__(*args, **kwargs)

        if not self.parent and parse is True:
            logger.debug("Starting automatic arg_parse")
            self.dispatch(*args)
