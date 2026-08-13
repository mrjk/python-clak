"""CLI descriptors: Argument, SubParser, MetaSetting, docstring helpers.

Extracted from parser.py to keep the build/execute core smaller.
Public imports remain available from ``clak``, ``clak.parser``, and
``clak.core.descriptors``.
"""

import logging
from typing import Any, Dict, Optional, Tuple, TypeVar

from clak.common import CleandocProxy, deindent_docstring
from clak.core.argparse_ import (
    SUPPRESS,
    argparse,
    argparse_inject_as_subparser,
)
from clak.core.nodes import Fn

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

    Handles both positional arguments and optional flags, choosing the
    appropriate argparse form from the flag names. Optional helpers
    :class:`Arg` (positionals) and :class:`Opt` (flags) reject mixed names.

    Most keyword arguments are passed through to
    :meth:`argparse.ArgumentParser.add_argument`. Clak-only kwargs (stripped
    before argparse):

    - ``argument_group`` / ``option_group``: Optional title for a help section
      (``parser.add_argument_group``). Same title reuses one section; pick the
      name that matches what you are grouping. Do not set both on one Argument.
    - ``exclusive_group``: Shared key for argparse mutual exclusion
      (``add_mutually_exclusive_group``). Same key reuses one XOR set
      (``required=False``). May nest under a help section when a help-group
      kwarg is also set.
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
        kwargs = dict(kwargs)
        if not isinstance(args, tuple):
            raise TypeError(
                f"Args must be a tuple for {self.__class__.__name__}: {type(args)}"
            )

        argument_group_title = kwargs.pop("argument_group", None)
        option_group_title = kwargs.pop("option_group", None)
        exclusive_key = kwargs.pop("exclusive_group", None)

        if argument_group_title is not None and option_group_title is not None:
            raise ValueError(
                f"Argument {key!r} cannot set both argument_group and "
                f"option_group (got {argument_group_title!r} and "
                f"{option_group_title!r})"
            )
        help_group_title = (
            argument_group_title
            if argument_group_title is not None
            else option_group_title
        )

        # Create argument
        logger.debug(
            "Create new argument %s.%s: %s",
            config.get_fname(attr="key"),
            key,
            self.kwargs,
        )

        target = parser
        if help_group_title is not None:
            groups = getattr(parser, "_clak_argument_groups", None)
            if groups is None:
                groups = {}
                setattr(parser, "_clak_argument_groups", groups)
            if help_group_title not in groups:
                groups[help_group_title] = parser.add_argument_group(help_group_title)
            target = groups[help_group_title]

        if exclusive_key is not None:
            exclusive_groups = getattr(parser, "_clak_exclusive_groups", None)
            if exclusive_groups is None:
                exclusive_groups = {}
                setattr(parser, "_clak_exclusive_groups", exclusive_groups)
            # Nest under the help section when present; key by (parent id, name)
            # so the same exclusive name can exist under different help titles.
            exclusive_cache_key = (id(target), exclusive_key)
            if exclusive_cache_key not in exclusive_groups:
                exclusive_groups[exclusive_cache_key] = (
                    target.add_mutually_exclusive_group()
                )
            target = exclusive_groups[exclusive_cache_key]

        target.add_argument(*args, **kwargs)

        return parser


def _check_arg_opt_names(args, expect_option: bool, cls_name: str) -> None:
    """Reject mixed positional names and option flags on Arg/Opt."""
    if not expect_option and not args:
        raise ValueError(
            f"{cls_name}() requires a positional name. "
            "Use Opt() or Argument() for dest-derived flags."
        )
    for arg in args:
        is_flag = str(arg).startswith("-")
        if expect_option and not is_flag:
            raise ValueError(
                f"{cls_name}() is for option flags, got positional {arg!r}. "
                "Use Arg() or Argument() for positionals."
            )
        if not expect_option and is_flag:
            raise ValueError(
                f"{cls_name}() is for positional arguments, got option flag "
                f"{arg!r}. Use Opt() or Argument() for flags."
            )
        is_flag = str(arg).startswith("-")
        if expect_option and not is_flag:
            raise ValueError(
                f"{cls_name}() is for option flags, got positional {arg!r}. "
                "Use Arg() or Argument() for positionals."
            )
        if not expect_option and is_flag:
            raise ValueError(
                f"{cls_name}() is for positional arguments, got option flag "
                f"{arg!r}. Use Opt() or Argument() for flags."
            )


class Arg(Argument):
    """Optional sugar for a positional argument.

    Same ``*args`` / ``**kwargs`` as :class:`Argument`, but at least one
    positional name is required (no leading ``-``). Empty ``Arg()`` is
    rejected; dest-derived flags belong on ``Opt`` / ``Argument``.
    ``Argument`` still accepts both positionals and flags.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _check_arg_opt_names(self.args, expect_option=False, cls_name="Arg")


class Opt(Argument):
    """Optional sugar for an option flag.

    Same ``*args`` / ``**kwargs`` as :class:`Argument`. When names are
    given, every name must start with ``-`` / ``--``. Empty ``Opt()`` is
    allowed: the attribute name becomes a dest-derived flag (``--attr``
    or ``-x``). ``Argument`` still accepts both positionals and flags.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _check_arg_opt_names(self.args, expect_option=True, cls_name="Opt")


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
            parser_kwargs = dict(self.kwargs)
            parser_kwargs.update(
                {
                    "formatter_class": config.get_help_formatter_class(),
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
            subparser.formatter_class = child.get_help_formatter_class()

            # pprint (subparser.__dict__)

        else:
            # This part is in BETA

            # Create nested structure
            child = self.cls(parent=config)
            # Pass help text from Command class kwargs
            child.parser.help = self.kwargs.get("help", child.__doc__)
            argparse_inject_as_subparser(config.parser, key, child.parser)

        return child


def first_doc_line(text: Optional[str]) -> str:
    """Get the first non-empty line from a text string.

    Args:
        text: The text to extract the first line from (None treated as empty)

    Returns:
        str: The first non-empty line, or empty string if no non-empty lines found

    Raises:
        ValueError: If first non-empty line starts with spaces
    """
    if not text:
        return ""
    lines = text.split("\n")
    for line in lines:
        if line.strip():
            if line.startswith(" "):
                raise ValueError(
                    f"First line of docstring should not start with spaces: {line}"
                )
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
        TypeError: If variables arg is not a dict
    """

    variables = variables or {}
    if not isinstance(variables, dict):
        raise TypeError(f"Got {type(variables)} instead of dict")

    if text is None:
        return None
    if text == SUPPRESS:
        return SUPPRESS

    text = deindent_docstring(text, reindent=reindent)
    try:
        text = text.format(**variables)
    except KeyError as err:
        logger.exception(
            "Error formatting docstring: %s; variables=%s; text=%s",
            err,
            variables,
            text,
        )
        raise

    return text


class FormatEnv:  # pylint: disable=too-few-public-methods
    "Format env for docstring variable substitution"

    _default = {
        "type": "type FUNC",
    }

    def __init__(self, variables=None):
        self._variables = dict(variables or {})

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


class MetaSetting(Fn):  # pylint: disable=too-few-public-methods
    "A setting that is used to configure a node"
