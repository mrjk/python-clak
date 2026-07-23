"""CLI descriptors: Argument, SubParser, MetaSetting, docstring helpers.

Extracted from parser.py to keep the build/execute core smaller.
Public imports remain available from ``clak.parser`` and ``clak``.
"""

import logging
from typing import Any, Dict, Optional, Tuple, TypeVar

from clak.argparse_ import (
    SUPPRESS,
    RecursiveHelpFormatter,
    argparse,
    argparse_inject_as_subparser,
)
from clak.common import CleandocProxy, deindent_docstring
from clak.nodes import Fn

logger = logging.getLogger(__name__)

# Keep this as True for performance reasons,
# children nodes will be considered as subparsers and not other parsers to be
# injected into the parent parser. The latter is slower.

USE_SUBPARSERS = True
# USE_SUBPARSERS = False    # BETA - Do not enable this, it is slower

T = TypeVar("T")  # For generic type hints


class ArgParseItem(Fn):
    """Base class for argument parser items.

    This class represents a generic argument parser item that can be added to an argument parser.
    It provides common functionality for handling destinations and building parameter dictionaries.

    Attributes:
        _destination (str): The destination name for the argument value
    """

    _destination: str = None

    @property
    def destination(self) -> Optional[str]:
        """Get the destination name for this argument.

        Returns:
            str: The destination name, derived from the argument name if not explicitly set
            None: If no destination can be determined
        """
        return self._get_best_dest()

    @destination.setter
    def destination(self, value):
        self._destination = value

    def _get_best_dest(self) -> str:
        "Get the best destination name for this argument"
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

    def build_params(self, dest: str) -> Tuple[tuple, dict]:
        """Build parameter dictionary for argument parser.

        Args:
            dest (str): Destination name for the argument

        Returns:
            tuple: A tuple containing (args, kwargs) for argument parser

        Raises:
            ValueError: If no arguments are found
        """
        # Create parser arguments
        kwargs = self.kwargs

        # kind = "option"
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
                # kind = "argument"

        elif dest:
            if len(dest) <= 2:
                args = (f"-{dest}",)
            else:
                args = (f"--{dest}",)
        else:
            raise ValueError(
                f"No arguments found for {self.__class__.__name__}: {self.__dict__}"
            )

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
        #             raise ValueError(
        #                 f"Too many arguments found for {self.__class__.__name__}: {self.__dict__}"
        #             )

        return args, kwargs


# Developper objects


class Argument(ArgParseItem):
    """Represents an argument that can be added to an argument parser.

    This class handles both positional arguments and optional flags, automatically determining
    the appropriate type based on the argument format.
    """

    def attach_arg_to_parser(self, key: str, config: "ParserNode") -> argparse.Action:
        """Create and add an argument to the parser.

        Args:
            key (str): The argument key/name
            config (ParserNode): The parser configuration object

        Returns:
            argparse.Action: The created argument parser action
        """
        parser = config.parser
        args, kwargs = self.build_params(key)
        assert isinstance(
            args, tuple
        ), f"Args must be a list for {self.__class__.__name__}: {type(args)}"

        # Create argument
        logger.debug(
            "Create new argument %s.%s: %s",
            config.get_fname(attr="key"),
            key,
            self.kwargs,
        )

        parser.add_argument(*args, **kwargs)

        return parser


class SubParser(ArgParseItem):
    """Represents a subcommand parser that can be added to a parent parser.

    This class handles creation of nested command structures, allowing for hierarchical
    command-line interfaces. It supports both subparser and injection modes.

    Attributes:
        meta__help_flags (bool): Whether to enable -h and --help support
        meta__usage (str): Custom usage message
        meta__description (str): Custom description message
        meta__epilog (str): Custom epilog message
    """

    # If true, enable -h and --help support
    meta__help_flags = True

    meta__usage = None
    meta__description = None
    meta__epilog = None

    def __init__(self, cls, *args, use_subparsers: bool = USE_SUBPARSERS, **kwargs):
        super().__init__(*args, **kwargs)
        self.cls = cls
        self.use_subparsers = use_subparsers

    def attach_sub_to_parser(self, key: str, config: "ParserNode") -> "ParserNode":
        """Create a subcommand parser for this command.

        Creates a new subparser for the command and configures it with the appropriate
        help text and options. Validates that the command name is valid.

        Args:
            key (str): Name of the subcommand
            config (ParserNode): Parent parser configuration object

        Raises:
            ValueError: If command name contains spaces

        Returns:
            ParserNode: The created child parser instance
        """

        if " " in key:
            raise ValueError(
                f"Command name '{key}' contains spaces. Command names must not contain spaces."
            )

        if self.use_subparsers:

            logger.debug(
                "Create new subparser %s.%s",
                config.get_fname(attr="key"),
                key,
            )  # , self.kwargs)

            # Fetch help from class
            parser_help = self.kwargs.get(
                "help",
                self.cls.query_cfg_inst(
                    self.cls, "help_description", default=self.cls.__doc__
                ),
            )
            parser_help_enabled = self.kwargs.get(
                "help_flags",
                self.cls.query_cfg_inst(self.cls, "help_flags", default=True),
            )
            # parser_aliases = self.kwargs.get(
            #     "aliases",
            #     [],
            # )

            ctx_vars = {"key": key, "self": config}

            # Create a new subparser for this command (flat structure)
            parser_help = prepare_docstring(
                first_doc_line(parser_help), variables=ctx_vars
            )
            parser_kwargs = self.kwargs
            parser_kwargs.update(
                {
                    "formatter_class": RecursiveHelpFormatter,
                    "add_help": parser_help_enabled,  # Add support for --help
                    "exit_on_error": False,
                    "help": parser_help,
                    # "aliases": parser_aliases,
                }
            )
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

            # logger.debug(
            #     "Create new SUBPARSER %s %s %s",
            #     child.get_fname(attr="key"),
            #     key,
            #     self.kwargs,
            # )

            child_usage = child.query_cfg_inst("help_usage", default=None)
            child_desc = first_doc_line(
                child.query_cfg_inst("help_description", default=child.__doc__)
            )
            child_epilog = child.query_cfg_inst("help_epilog", default=None)
            # print(f"DESC: |{desc}|")

            # Reconfigure subparser
            child_usage = prepare_docstring(child_usage, variables=ctx_vars)
            child_desc = prepare_docstring(child_desc, variables=ctx_vars)
            child_epilog = prepare_docstring(child_epilog, variables=ctx_vars)

            subparser.add_help = (
                False  # child.query_cfg_inst("help_enable", default=True)
            )
            subparser.usage = child_usage
            subparser.description = child_desc
            subparser.epilog = child_epilog

            # pprint (subparser.__dict__)

        else:
            # This part is in BETA

            # Create nested structure
            child = self.cls(parent=config)
            # Pass help text from Command class kwargs
            child.parser.help = self.kwargs.get("help", child.__doc__)
            argparse_inject_as_subparser(config.parser, key, child.parser)

        return child


class RegistryEntry:
    "Registry entry"

    def __init__(self, config):
        # super().__init__(*args, **kwargs)
        # self.parser = None
        self._config = config
        self._entries = {}

    def add_entry(self, key: str, value: Any) -> None:
        """Add a new entry to the registry.

        Args:
            key: Key to store the entry under
            value: Value to store in the registry
        """
        self._entries[key] = value

    def __repr__(self):
        return f"RegistryEntry({self._config})"


def first_doc_line(text: str) -> str:
    """Get the first non-empty line from a text string.

    Args:
        text (str): The text to extract the first line from

    Returns:
        str: The first non-empty line, or empty string if no non-empty lines found

    Raises:
        AssertionError: If first non-empty line starts with spaces
    """
    lines = text.split("\n")
    for line in lines:
        if line.strip():
            assert not line.startswith(
                " "
            ), f"First line of docstring should not start with 2 spaces: {line}"
            return line
    return ""


def prepare_docstring(
    text: Optional[str], variables: Optional[Dict[str, Any]] = None, reindent: str = ""
) -> Optional[str]:
    """Prepare a docstring by deindenting and formatting with variables.

    Args:
        text (str): The docstring text to prepare
        variables (dict, optional): Variables to format into the docstring
        reindent (str, optional): String to use for reindenting

    Returns:
        str: The prepared docstring, or None/SUPPRESS if input was None/SUPPRESS

    Raises:
        KeyError: If formatting fails due to missing variables
        AssertionError: If variables arg is not a dict
    """

    variables = variables or {}
    assert isinstance(variables, dict), f"Got {type(variables)} instead of dict"

    if text is None:
        return None
    if text == SUPPRESS:
        return SUPPRESS

    text = deindent_docstring(text, reindent=reindent)
    try:
        text = text.format(**variables)
    except KeyError as err:
        print(f"Error formatting docstring: {err}")
        print(f"Variables: {variables}")
        print(f"Text: {text}")
        raise err

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
        for key, value in self._variables.items():
            # Normalize object.__doc__ across Python versions (3.13+ cleandoc).
            if key == "self" and value is not None:
                out[key] = CleandocProxy(value)
            else:
                out[key] = value
        return out

    def __dict__(self):
        return dict(self.get())


class MetaSetting(Fn):  # pylint: disable=too-few-public-methods
    "A setting that is used to configure a node"
