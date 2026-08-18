"""Argparse helpers: inject (BETA), re-exports from argp and help_render."""

# pylint: disable=protected-access unused-import

import argparse

from clak.core.argp import (  # noqa: F401
    ONE_OR_MORE,
    OPTIONAL,
    PARSER,
    REMAINDER,
    SUPPRESS,
    ZERO_OR_MORE,
    ArgparseCapabilities,
    ArgumentError,
    ArgumentParser,
    ArgumentParserPlus,
    ErrorRenderer,
    argparse,
    format_argument_error,
)
from clak.core.help_render import (  # noqa: F401
    HELP_NESTED_INDENT,
    HELP_SUBCOMMANDS_ALL,
    HELP_SUBCOMMANDS_CHOICES,
    HELP_SUBCOMMANDS_TOP,
    HelpLayout,
    HelpRenderer,
    RecursiveHelpFormatter,
    help_layout_for,
)


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
