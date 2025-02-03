"""Enhanced argument parsing functionality for the Clak framework.

This module extends Python's built-in argparse module with additional features
needed by Clak, including:

- Custom Action class with Clak-specific configuration
- Helper functions for merging and injecting parsers
- Utilities for managing parser hierarchies

The module re-exports common argparse elements while providing its own enhanced
versions of core classes.
"""

# pylint: disable=protected-access unused-import


import argparse
import logging
from argparse import ONE_OR_MORE, OPTIONAL, SUPPRESS, ZERO_OR_MORE, ArgumentError

# from argparse import OPTIONAL, SUPPRESS, ZERO_OR_MORE, ArgumentError
from gettext import gettext as _
from pprint import pprint
from types import SimpleNamespace

# import argcomplete

# Expose common argparse elements


logger = logging.getLogger(__name__)

# SUPPRESS = argparse.SUPPRESS
# OPTIONAL = argparse.OPTIONAL
# ZERO_OR_MORE = argparse.ZERO_OR_MORE


# # Store the original Action class
# _OriginalAction = _argparse.Action


# # Create your new Action class
# class Action(_OriginalAction):  # pylint: disable=too-few-public-methods
#     """Enhanced version of argparse.Action with custom behavior"""

#     def __init__(self, *args, clak_config=None, **kwargs) -> None:
#         super().__init__(*args, **kwargs)
#         self.clak_config = clak_config


# # Replace the original Action class
# _argparse.Action = Action

# argparse = _argparse

# Version: v4

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


# Merge parent argparsers, and create on merged child.
def argparse_merge_parents(
    *parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """Merge X parsers with their subparsers into a new one."""
    parents = list(*parser)
    # TOfix, first parent should inherit default settings
    merged_parser = argparse.ArgumentParser(
        description="Merged parser example with subcommands",
        add_help=True,
        parents=parents,
        conflict_handler="resolve",  # Required to avoid conflicts when help is enabled
        formatter_class=RecursiveHelpFormatter,
    )
    return merged_parser


# Inject a argparser into a subkey of a parent parser.
def argparse_inject_as_subparser(parent_parser, key, child_parser):
    """Merge a child parser into a parent parser under a specific key.

    Args:
        parent_parser: The main parser to add the child to
        key: The subcommand name under which to add the child parser
        child_parser: The parser to merge in as a subcommand
    """
    # Find the existing subparsers object in the parent parser
    parent_subparsers = None
    for action in parent_parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            parent_subparsers = action
            break

    if parent_subparsers is None:
        parent_subparsers = parent_parser.add_subparsers(
            dest="command", help="Available commands"
        )

    # Create the new subparser with the given key
    subparser = parent_subparsers.add_parser(
        key,
        help=child_parser.description
        or getattr(child_parser, "help", f"Commands from {key}"),
        description=child_parser.description,
        formatter_class=child_parser.formatter_class,
    )

    def get_action_kwargs(action):
        """Helper to get kwargs for an action based on its type."""
        kwargs = {
            "help": action.help,
            "default": action.default if action.default is not None else None,
            "type": action.type if action.type != str else None,
            "choices": action.choices if hasattr(action, "choices") else None,
            "metavar": action.metavar if hasattr(action, "metavar") else None,
        }

        # Handle different action types
        if isinstance(action, argparse._StoreConstAction):
            kwargs["action"] = "store_const"
            kwargs["const"] = action.const
        elif isinstance(action, argparse._StoreTrueAction):
            kwargs["action"] = "store_true"
        elif isinstance(action, argparse._StoreFalseAction):
            kwargs["action"] = "store_false"
        elif isinstance(action, argparse._AppendConstAction):
            kwargs["action"] = "append_const"
            kwargs["const"] = action.const
        elif isinstance(action, argparse._CountAction):
            kwargs["action"] = "count"
        elif isinstance(action, argparse._AppendAction):
            kwargs["action"] = "append"
            if hasattr(action, "nargs"):
                kwargs["nargs"] = action.nargs
        elif hasattr(action, "nargs"):
            kwargs["nargs"] = action.nargs

        # Clean up kwargs
        return {k: v for k, v in kwargs.items() if v is not None}

    def copy_parser_with_subcommands(source_parser, target_parser, prefix=""):
        """Recursively copy a parser and all its subcommands."""
        # Copy all arguments except help
        for action in source_parser._actions:
            if isinstance(action, argparse._HelpAction):
                continue

            if isinstance(action, argparse._SubParsersAction):
                # Create subparsers with the same help text
                target_subparsers = target_parser.add_subparsers(
                    dest=f"{prefix}command" if prefix else "command", help=action.help
                )

                # Copy each subcommand
                for choice, choice_parser in action.choices.items():
                    # Find the matching choice action to get the help text
                    choice_help = next(
                        (
                            subaction.help
                            for subaction in action._choices_actions
                            if subaction.dest == choice
                        ),
                        None,
                    )
                    new_parser = target_subparsers.add_parser(
                        choice,
                        help=choice_help,
                        description=choice_parser.description,
                        formatter_class=choice_parser.formatter_class,
                    )
                    # Recursively copy the subcommand parser
                    copy_parser_with_subcommands(
                        choice_parser, new_parser, f"{prefix}{choice}_"
                    )
            else:
                kwargs = get_action_kwargs(action)
                if action.option_strings:
                    # Handle optional arguments
                    kwargs["dest"] = action.dest
                    if hasattr(action, "required"):
                        kwargs["required"] = action.required
                    target_parser.add_argument(*action.option_strings, **kwargs)
                else:
                    # Handle positional arguments
                    target_parser.add_argument(action.dest, **kwargs)

    # Copy the child parser and all its subcommands
    copy_parser_with_subcommands(child_parser, subparser, f"{key}_")

    return parent_parser


# Inherit from Raw formatter.
class RecursiveHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """A recursive help formatter to help command discovery."""

    config__max_help_position = 30

    def __init__(self, *args, max_help_position=None, **kwargs):
        super().__init__(
            *args, max_help_position=self.config__max_help_position, **kwargs
        )

    def _get_default_metavar_for_positional(self, action):
        "Automatically show positional as uppercase"
        return action.dest.upper()

    # Show default values
    def _get_help_string(self, action):
        help_msg = action.help
        if help_msg is None:
            help_msg = ""

        if "%(default)" not in help_msg:
            if action.default is not SUPPRESS:
                defaulting_nargs = [OPTIONAL, ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help_msg += " (default: %(default)s)"
        return help_msg

    # Ensure all subparsers are shown
    def _format_action(self, action):
        "Override and improve helper output"

        # Notes:
        # Why not use add_argument_group()?
        # - See: https://docs.python.org/3/library/argparse.html#argument-groups
        # Implement register for subcommands:
        # - See: https://docs.python.org/3/library/argparse.html#registering-custom-types-or-actions

        if not isinstance(action, argparse._SubParsersAction):
            out = super()._format_action(action)
            return out

        # Get the original format parts
        parts = []
        bullet: str = "  "

        help_position = min(self._action_max_length + 2, self._max_help_position)
        # help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2

        def add_subparser_to_parts(
            parser: argparse.ArgumentParser,
            prefix: str = "",
            level: int = 0,
            indent: str = "..",
        ):
            _indent = indent * level

            for act in parser._actions:
                if isinstance(act, argparse._SubParsersAction):
                    for subaction in act._choices_actions:
                        choice = act.choices[subaction.dest]
                        cmd = f"{prefix}{subaction.dest}"
                        if subaction.help != argparse.SUPPRESS:
                            help_msg = subaction.help or ""
                            line = f"{_indent}{bullet}"
                            # TOFIX: Check if line > help_width
                            line = f"{line}{cmd:<{action_width}}{help_msg}\n"
                            parts.append(line)
                            cmd = f"{cmd}"

                        add_subparser_to_parts(
                            choice, prefix=f"{cmd} ", level=level + 1, indent=indent
                        )

        # Format all commands with alignment
        for subaction in action._choices_actions:
            # pprint(subaction.__dict__)

            choice = action.choices[subaction.dest]
            if subaction.help != argparse.SUPPRESS:
                help_msg = subaction.help or ""
                # TOFIX: Check if line > help_width
                line = f"{bullet}{subaction.dest:<{action_width}}{help_msg}\n"
                parts.append(line)
            add_subparser_to_parts(
                choice, prefix=f"{subaction.dest} ", level=1, indent=""
            )

        if len(parts) > 0:
            parts.insert(0, "\nsubcommands:\n")

        return "".join(parts)


class ArgumentParserPlus(argparse.ArgumentParser):
    "Improved version of ArgumentParser"

    def __init__(self, *args, clak_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.clak_instance = clak_instance

    def parse_args(self, args=None, namespace=None):
        args, argv = self.parse_known_args(args, namespace)
        if argv:
            msg = _("unrecognized arguments: %s") % " ".join(argv)
            if self.exit_on_error:
                self.error(msg)
            else:
                raise argparse.ArgumentError(None, msg)
        return args
