"""Clak parser: ParserNode build, dispatch, and execute.

Descriptors (Argument, Arg, Opt, SubParser, MetaSetting, docstring helpers)
live in ``clak.core.descriptors``.

Canonical public names: ``Parser``, ``Argument``, ``Command`` (alias of SubParser).
Optional helpers: ``Arg`` (positionals), ``Opt`` (flags).
Instantiate a root ``Parser`` to parse and run; it calls ``dispatch()`` automatically
unless ``parse=False``.

Dispatch and exception handling live in ``clak.core._dispatch`` and
``clak.core._exception``; this module keeps the build/inherit facade.
"""

import argparse
import logging
from typing import Any, Optional

from clak import exception
from clak.core._dispatch import Dispatcher
from clak.core._exception import clean_terminate
from clak.core.argp import ArgumentParser as ClakArgumentParser
from clak.core.argp import SubParsersAction
from clak.core.argp.actions import HelpAllAction
from clak.core.context import ClakContext
from clak.core.descriptors import (
    Argument,
    MetaSetting,
    SubParser,
    first_doc_line,
    prepare_docstring,
)
from clak.core.help_render import (
    HELP_SUBCOMMANDS_ALL,
    HelpLayout,
    HelpRenderer,
    RichRecursiveHelpFormatter,
    help_document_colorizer,
    topic_flag,
)
from clak.core.nodes import NOT_SET, Node
from clak.runtime.settings import apply_debug_logging

logger = logging.getLogger(__name__)

# Public name for subcommand descriptors (SubParser is the class).
Command = SubParser

PROPAGATE_OPTIONS_GROUP_DEFAULT = "parent options"

# Mixin plugin convention: a mixin contributes behavior by defining
# ``cli_hook__<name>(self, instance, ctx, **_)`` methods. They are collected
# at build time and run for every node of the command path, before
# ``cli_group`` / ``cli_run``. Read configuration from ``instance`` (the node
# being walked) so a subcommand's ``Meta`` wins.
CLI_HOOK_PREFIX = "cli_hook__"


class ParserNode(
    Node
):  # pylint: disable=too-many-instance-attributes,too-many-public-methods
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
    3. Implementing cli_run() for command implementation
    4. Implementing cli_group() for command group behavior

    Attributes:
        children (dict): Dictionary of subcommand name to child parser
        meta__name (str): ParserNode name
    """

    meta__name: str = NOT_SET

    meta__subcommands_dict: dict[str, SubParser] = {}
    meta__arguments_dict: dict[str, Argument] = {}

    meta__cli_view = None  # ClakView instance or subclass (see Meta.cli_view)

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
    meta__config__abbrev_commands = MetaSetting(
        help=(
            "Accept a unique prefix of a subcommand name, e.g. 'bu' for "
            "'buzz' (default True). Inherited; ambiguous prefixes error."
        ),
    )
    meta__config__abbrev_options = MetaSetting(
        help=(
            "Accept a unique prefix of a long flag, e.g. '--verb' for "
            "'--verbose' (default True, argparse allow_abbrev). Inherited."
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
    meta__config__help_collapsed_groups = MetaSetting(
        help=(
            "Option group titles summarized in short --help and listed by "
            "--help-all (default: 'output options' and the propagated group; "
            "[] disables). Inherited."
        ),
    )
    meta__config__help_all_flag = MetaSetting(
        help="Flag printing the full help (default '--help-all'; None disables)",
    )
    meta__config__help_split = MetaSetting(
        help=(
            "-h prints the short help, --help the full one (default False; "
            "disables --help-all and --help-<topic>). Inherited; see LongHelpMixin."
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

        if parent is None:
            apply_debug_logging()

        super().__init__(parent=parent)

        self.dispatcher = Dispatcher(self)
        self.help_args = []
        self.command_group = None
        self.command_help = None

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
            # add_parser() builds ClakArgumentParser without clak_instance.
            if hasattr(self.parser, "clak_instance"):
                self.parser.clak_instance = self

        self._install_help_flag()

        # Init _subparsers
        self._subparsers = None
        self.local_flag_arguments: dict[str, Argument] = {}

        self.add_arguments()
        self.add_subcommands()
        self._cli_hooks = self._collect_cli_hooks()
        self._install_help()

    def __repr__(self):
        return f"<{self.__class__.__module__}.{self.__class__.__name__}>"

    def help_texts(self, variables: dict, first_line: bool = False) -> tuple:
        """Return prepared ``(usage, description, epilog)`` for this node.

        Reads ``Meta.help_usage`` / ``help_description`` (default: class
        docstring) / ``help_epilog`` and formats them with *variables*.
        *first_line* keeps only the description's first line (subcommands).
        """
        desc = self.query_cfg_inst("help_description", default=self.__doc__)
        if first_line:
            desc = first_doc_line(desc)
        texts = (
            self.query_cfg_inst("help_usage", default=None),
            desc,
            self.query_cfg_inst("help_epilog", default=None),
        )
        return tuple(prepare_docstring(text, variables=variables) for text in texts)

    def create_parser(self):
        "Create a new parser"
        usage, desc, epilog = self.help_texts({"self": self})
        # parse_intermixed / allow_abbrev are set by _install_help.
        parser = ClakArgumentParser(
            prog=self.proc_name,
            usage=usage,
            description=desc,
            epilog=epilog,
            formatter_class=self.get_help_formatter_class(),
            add_help=False,  # help flags are owned by _install_help_flags
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
        return self.query_cfg_parents(
            "help_formatter",
            default=RichRecursiveHelpFormatter,
        )

    def _resolve_collapsed_groups(self) -> tuple:
        groups = self.query_cfg_parents("help_collapsed_groups", default=None)
        if groups is None:
            groups = (
                "output options",
                self.query_cfg_parents(
                    "propagate_options_group", default=PROPAGATE_OPTIONS_GROUP_DEFAULT
                ),
            )
        return tuple(groups)

    def _resolve_help_all_flag(self) -> Optional[str]:
        if self._is_help_split():
            return None
        flag = self.query_cfg_parents("help_all_flag", default="--help-all")
        return flag if flag and self.add_help else None

    def _is_help_split(self) -> bool:
        return bool(self.query_cfg_parents("help_split", default=False))

    def _install_help_topics(self, all_flag: str) -> None:
        """Add ``--help-<topic>`` for each non-empty collapsed group."""
        present = {a.group for a in self.help_args if not a.is_hidden()}
        for title in self.help_layout.collapsed_groups:
            flag = topic_flag(title)
            if title in present and flag != all_flag:
                self.parser.add_argument(
                    flag,
                    action=HelpAllAction,
                    const=title,
                    dest=f"help_{flag[7:].replace('-', '_')}",
                    default=argparse.SUPPRESS,
                    help=argparse.SUPPRESS,
                )

    def _install_help_flag(self) -> None:
        """Register ``-h/--help``; runs first so it leads usage and options."""
        if not self.add_help or not hasattr(self.parser, "add_argument"):
            return
        opts = dict(default=argparse.SUPPRESS)
        if self._is_help_split():
            self.parser.add_argument(
                "-h", action="help", dest="help",
                help="show the short help and exit", **opts
            )
            self.parser.add_argument(
                "--help",
                action=HelpAllAction,
                dest="help_all",
                help="show the full help, including all options, and exit",
                **opts,
            )
        else:
            self.parser.add_argument(
                "-h", "--help", action="help",
                help="show this help message and exit", **opts,
            )

    def _install_help_flags(self) -> None:
        """Register ``--help-all`` and ``--help-<topic>`` (needs the layout)."""
        if not self.add_help or not hasattr(self.parser, "add_argument"):
            return
        flag = self.help_layout.help_all_flag
        if flag:
            self.parser.add_argument(
                flag,
                action=HelpAllAction,
                dest="help_all",
                default=argparse.SUPPRESS,
                help=argparse.SUPPRESS,
            )
            self._install_help_topics(flag)

    def _install_help(self):
        """Attach HelpRenderer and version-stable parse flags to the wrapper."""
        self.help_layout = HelpLayout(
            subcommands=self.query_cfg_parents(
                "help_subcommands",
                default=HELP_SUBCOMMANDS_ALL,
            ),
            hide_parent=self.query_cfg_parents(
                "help_hide_parent",
                default=True,
            ),
            command_groups=tuple(
                self.query_cfg_inst("command_groups", default=()) or ()
            ),
            collapsed_groups=self._resolve_collapsed_groups(),
            help_all_flag=self._resolve_help_all_flag(),
            help_split=self._is_help_split(),
        )
        renderer = HelpRenderer(self)
        fmt = self.get_help_formatter_class()
        if isinstance(fmt, type) and issubclass(fmt, RichRecursiveHelpFormatter):
            renderer.colorizer = help_document_colorizer
        self.help_renderer = renderer
        self._install_help_flags()
        if hasattr(self.parser, "clak_help_renderer"):
            self.parser.clak_help_renderer = renderer
        if hasattr(self.parser, "parse_intermixed"):
            self.parser.parse_intermixed = self.query_cfg_parents(
                "parse_intermixed", default=True
            )
        # Subparsers built by add_parser() get argparse's default; read at
        # parse time, so setting it after build is enough.
        self.parser.allow_abbrev = bool(
            self.query_cfg_parents("abbrev_options", default=True)
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
                parser_class=ClakArgumentParser,
                action=SubParsersAction,
                allow_abbrev=bool(
                    self.query_cfg_parents("abbrev_commands", default=True)
                ),
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
        1. Collects arguments from meta__arguments_dict
        2. Collects arguments defined as class attributes
        3. Adds internal arguments like __cli_self__
        4. Creates all argument parser entries
        5. Copies ancestor flags onto this parser when inherit is on
        """
        if arguments is None:
            arguments = getattr(self, "meta__arguments_dict", None)
        arguments = self._collect_descriptors(
            arguments, Argument, skip=self._skip_argument_names()
        )

        # Add __cli_self__ argument
        arguments["__cli_self__"] = Argument(help=argparse.SUPPRESS, default=self)

        ancestor_dests, ancestor_strings = self._ancestor_flag_index()
        local_flags: dict[str, Argument] = {}

        for key, arg in arguments.items():
            arg = self._prepare_argument(key, arg)
            overrides = None
            flag_strings = arg.flag_strings(key)
            if flag_strings:
                local_flags[key] = arg
                if key in ancestor_dests or (ancestor_strings & set(flag_strings)):
                    overrides = arg.suppress_attach_overrides()
            self.add_argument(key, arg, attach_overrides=overrides)

        self.local_flag_arguments = local_flags

        if self.query_cfg_parents("propagate_options", default=True):
            self._attach_inherited_parent_flags(arguments, local_flags)

    def _collect_descriptors(self, explicit, kind, skip=()) -> dict:
        """``{name: descriptor}``: *explicit* dict, then class attrs of *kind*.

        Walks the MRO so a subclass attribute wins over an inherited one;
        class attributes named in *skip* are ignored.
        """
        if explicit is None:
            explicit = {}
        if not isinstance(explicit, dict):
            raise TypeError(f"Got {type(explicit)} instead of dict")
        found = dict(explicit)
        for cls in type(self).__mro__:
            for name, value in vars(cls).items():
                if isinstance(value, kind) and name not in found and name not in skip:
                    found[name] = value
        return found

    def _iter_ancestor_flags(self):
        """``(dest, Argument)`` flags defined locally on ancestors, closest first."""
        node = self.parent
        while node:
            yield from node.local_flag_arguments.items()
            node = node.parent

    def _ancestor_flag_index(self) -> tuple[set[str], set[str]]:
        """Dests and option strings from ancestors' locally defined flags."""
        dests: set[str] = set()
        strings: set[str] = set()
        for dest, arg in self._iter_ancestor_flags():
            dests.add(dest)
            strings.update(arg.flag_strings(dest))
        return dests, strings

    def _attach_inherited_parent_flags(
        self, arguments: dict, local_flags: dict[str, Argument]
    ) -> None:
        """Copy closest ancestor flags onto this parser (default=SUPPRESS)."""
        seen_dests = set(arguments)
        seen_strings: set[str] = set()
        for dest, arg in local_flags.items():
            seen_strings.update(arg.flag_strings(dest))

        group = self.query_cfg_parents(
            "propagate_options_group",
            default=PROPAGATE_OPTIONS_GROUP_DEFAULT,
        )
        group_extra = {
            "option_group": group,
            "argument_group": None,
        }

        for dest, arg in self._iter_ancestor_flags():
            if dest in seen_dests or not arg.propagates():
                continue
            strings = arg.flag_strings(dest)
            if not strings or (seen_strings & set(strings)):
                continue
            self.add_argument(
                dest,
                arg,
                attach_overrides=arg.suppress_attach_overrides(extra=group_extra),
            )
            seen_dests.add(dest)
            seen_strings.update(strings)

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
        subcommands = self._collect_descriptors(subcommands, Command)

        for key, arg in subcommands.items():
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

    # Execution helpers
    # ========================

    def parse_args(self, *args, **kwargs):
        """Parse argv; see ``Dispatcher.parse_args``."""
        return self.dispatcher.parse_args(*args, **kwargs)

    def dispatch(self, *args, **kwargs):
        """Parse and run; see ``Dispatcher.dispatch``."""
        return self.dispatcher.dispatch(*args, **kwargs)

    def cli_execute(self, *args, **kwargs):
        """Walk hooks and ``cli_run``; see ``Dispatcher.cli_execute``."""
        return self.dispatcher.cli_execute(*args, **kwargs)

    def clean_terminate(self, *args, **kwargs):
        """Handle a dispatch error; see ``clak.core._exception.clean_terminate``."""
        return clean_terminate(self, *args, **kwargs)

    @property
    def ctx(self):
        """Last ``ClakContext`` from dispatch, or None before execute."""
        return self.dispatcher.ctx

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

    def _collect_cli_hooks(self) -> dict:
        """Bound ``cli_hook__*`` methods on this instance (once at build)."""
        hooks = {}
        for name in dir(self):
            if not name.startswith(CLI_HOOK_PREFIX):
                continue
            fn = getattr(self, name, None)
            if callable(fn):
                hooks[name] = fn
        return hooks

    def cli_group(self, ctx: ClakContext, **_: Any) -> None:
        """Execute group-level command behavior.

        Args:
            ctx: Command context object
            **_: Unused keyword arguments
        """


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
            # Positional args belong to ParserNode.__init__ (add_help, ...),
            # never to argv: dispatch reads sys.argv.
            self.dispatch()
