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
import re
import textwrap
from argparse import (
    ONE_OR_MORE,
    OPTIONAL,
    PARSER,
    REMAINDER,
    SUPPRESS,
    ZERO_OR_MORE,
    ArgumentError,
)
from dataclasses import dataclass

# from argparse import OPTIONAL, SUPPRESS, ZERO_OR_MORE, ArgumentError
from gettext import gettext as _
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


def format_argument_error(err: argparse.ArgumentError) -> str:
    """Build a stable Clak parse-error message from argparse.ArgumentError.

    ``argument_name`` is often ``None`` (e.g. missing required args). Avoid
    embedding the literal ``None`` in user-facing output.
    """
    parts = []
    if err.argument_name:
        parts.append(str(err.argument_name))
    if err.message:
        parts.append(str(err.message))
    detail = " ".join(parts) if parts else str(err)
    return f"Could not parse command line: {detail}"


HELP_SUBCOMMANDS_TOP = "top"
HELP_SUBCOMMANDS_ALL = "all"
HELP_SUBCOMMANDS_CHOICES = frozenset({HELP_SUBCOMMANDS_TOP, HELP_SUBCOMMANDS_ALL})
HELP_NESTED_INDENT = "  "


@dataclass
class HelpLayout:
    """Formatter listing policy, stashed on argparse ``_SubParsersAction``.

    Per-command membership stays on the choice action
    (``_clak_command_group``). Missing stash means these defaults.
    """

    subcommands: str = HELP_SUBCOMMANDS_ALL
    hide_parent: bool = True
    command_groups: tuple = ()

    def __post_init__(self):
        if self.subcommands not in HELP_SUBCOMMANDS_CHOICES:
            raise ValueError(
                "help_subcommands must be 'top' or 'all', " f"got {self.subcommands!r}"
            )
        if not isinstance(self.hide_parent, bool):
            raise ValueError(
                "help_hide_parent must be True or False, " f"got {self.hide_parent!r}"
            )
        if not isinstance(self.command_groups, tuple):
            self.command_groups = tuple(self.command_groups or ())


def help_layout_for(action) -> HelpLayout:
    """Return stashed layout, or defaults if the action has none."""
    layout = getattr(action, "_clak_help", None)
    if layout is None:
        return HelpLayout()
    return layout


# Inherit from Raw formatter.
class RecursiveHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """A recursive help formatter to help command discovery."""

    config__max_help_position = 30

    def __init__(self, *args, max_help_position=None, **kwargs):
        super().__init__(
            *args, max_help_position=self.config__max_help_position, **kwargs
        )

    def _format_action_invocation(self, action):
        """Keep option help stable across Python versions.

        Python 3.13+ changed optional formatting from
        ``-s ARGS, --long ARGS`` to ``-s, --long ARGS``. Pin the older form so
        Clak help output does not drift with the interpreter.
        """
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            (metavar,) = self._metavar_formatter(action, default)(1)
            return metavar

        parts = []
        if action.nargs == 0:
            parts.extend(action.option_strings)
        else:
            default = self._get_default_metavar_for_optional(action)
            args_string = self._format_args(action, default)
            for option_string in action.option_strings:
                parts.append(f"{option_string} {args_string}")
        return ", ".join(parts)

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

    @staticmethod
    def _grouped_subcommand_sections(action, layout=None):
        """Yield (title, choice actions) for named, unknown-key, then leftover."""
        if layout is None:
            layout = help_layout_for(action)
        named_groups = layout.command_groups or ()
        named_titles = dict(named_groups)
        named_keys = [key for key, _title in named_groups]

        by_group = {}
        for subaction in action._choices_actions:
            group_key = getattr(subaction, "_clak_command_group", None)
            by_group.setdefault(group_key, []).append(subaction)

        for key in named_keys:
            members = by_group.get(key)
            if members:
                yield named_titles[key], members

        unknown_keys = []
        for subaction in action._choices_actions:
            group_key = getattr(subaction, "_clak_command_group", None)
            if group_key is None or group_key in named_titles:
                continue
            if group_key not in unknown_keys:
                unknown_keys.append(group_key)
        for key in unknown_keys:
            title = key if str(key).endswith(":") else f"{key}:"
            yield title, by_group.get(key)

        leftover = by_group.get(None)
        if leftover:
            yield "subcommands:", leftover

    @staticmethod
    def _nested_cmd_label(prefix, dest, hide_parent, level=0):
        if hide_parent:
            return f"{HELP_NESTED_INDENT * level}{dest}"
        return f"{prefix}{dest}"

    def _max_subcommand_label_width(self, action, list_nested, hide_parent):
        """Longest left label among listed subcommands (nested when enabled)."""
        widest = 0

        def walk(parser, prefix, level):
            nonlocal widest
            for act in parser._actions:
                if not isinstance(act, argparse._SubParsersAction):
                    continue
                for subaction in act._choices_actions:
                    if subaction.help != argparse.SUPPRESS:
                        widest = max(
                            widest,
                            len(
                                self._nested_cmd_label(
                                    prefix, subaction.dest, hide_parent, level
                                )
                            ),
                        )
                    if list_nested:
                        walk(
                            act.choices[subaction.dest],
                            f"{prefix}{subaction.dest} ",
                            level + 1,
                        )

        for subaction in action._choices_actions:
            if subaction.help != argparse.SUPPRESS:
                widest = max(widest, len(subaction.dest))
            if list_nested:
                walk(action.choices[subaction.dest], f"{subaction.dest} ", 1)
        return widest

    # Ensure all subparsers are shown
    def _format_action(self, action):  # pylint: disable=too-many-locals
        "Override and improve helper output"

        # Notes:
        # Subcommand sections are formatter metadata (command_group), not
        # argparse add_argument_group / a second add_subparsers.
        # - See: https://docs.python.org/3/library/argparse.html#argument-groups
        # Implement register for subcommands:
        # - See: https://docs.python.org/3/library/argparse.html#registering-custom-types-or-actions

        if not isinstance(action, argparse._SubParsersAction):
            out = super()._format_action(action)
            return out

        layout = help_layout_for(action)
        list_nested = layout.subcommands == HELP_SUBCOMMANDS_ALL
        hide_parent = layout.hide_parent

        # Get the original format parts
        parts = []
        bullet: str = "  "
        # argparse pads invocation to action_width, then two spaces before help
        help_gap = "  "

        help_position = min(self._action_max_length + 2, self._max_help_position)
        action_width = help_position - self._current_indent - 2
        action_width = max(
            action_width,
            self._max_subcommand_label_width(action, list_nested, hide_parent) + 2,
        )
        max_action_width = self._max_help_position - self._current_indent - 2
        if max_action_width > 0:
            action_width = min(action_width, max_action_width)
        help_position = action_width + self._current_indent + 2
        help_width = max(self._width - help_position, 11)

        def format_cmd_line(cmd, help_msg, prefix=""):
            if not help_msg:
                return f"{prefix}{cmd}\n"
            if len(cmd) >= action_width:
                wrapped = textwrap.wrap(help_msg, help_width) or [""]
                lines = [f"{prefix}{cmd}"]
                lines.extend(f"{' ' * help_position}{chunk}" for chunk in wrapped)
                return "".join(f"{line}\n" for line in lines)
            return f"{prefix}{cmd:<{action_width}}{help_gap}{help_msg}\n"

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
                        full_cmd = f"{prefix}{subaction.dest}"
                        if subaction.help != argparse.SUPPRESS:
                            help_msg = subaction.help or ""
                            parts.append(
                                format_cmd_line(
                                    self._nested_cmd_label(
                                        prefix,
                                        subaction.dest,
                                        hide_parent,
                                        level,
                                    ),
                                    help_msg,
                                    prefix=f"{_indent}{bullet}",
                                )
                            )

                        add_subparser_to_parts(
                            choice,
                            prefix=f"{full_cmd} ",
                            level=level + 1,
                            indent=indent,
                        )

        def append_choice(subaction):
            choice = action.choices[subaction.dest]
            if subaction.help != argparse.SUPPRESS:
                help_msg = subaction.help or ""
                parts.append(format_cmd_line(subaction.dest, help_msg, prefix=bullet))
            if list_nested:
                add_subparser_to_parts(
                    choice, prefix=f"{subaction.dest} ", level=1, indent=""
                )

        grouped = any(
            getattr(subaction, "_clak_command_group", None)
            for subaction in action._choices_actions
        )
        if not grouped:
            for subaction in action._choices_actions:
                append_choice(subaction)
            if len(parts) > 0:
                parts.insert(0, "\nsubcommands:\n")
            return "".join(parts)

        for title, subactions in self._grouped_subcommand_sections(action, layout):
            parts.append(f"\n{title}\n")
            for subaction in subactions:
                append_choice(subaction)

        return "".join(parts)

    def format_help(self):
        """Drop an empty ``positional arguments:`` heading.

        Subparsers live in that argparse group, but Clak prints them under
        ``subcommands:``. When there are no real positionals, the empty
        heading is noise.

        RST double-backtick literals are stripped from rendered help.
        """
        text = super().format_help()
        heading = _("positional arguments")
        text = re.sub(rf"(?m)^{re.escape(heading)}:\n+(?! )", "", text)
        return text.replace("``", "")


class ArgumentParserPlus(argparse.ArgumentParser):
    """ArgumentParser with Clak-stable error behavior across Python versions.

    Python < 3.12 still calls ``error()`` for some failures (e.g. missing
    required args) even when ``exit_on_error=False``. Raise ``ArgumentError``
    instead so Clak can always handle parse errors the same way.
    """

    def __init__(self, *args, clak_instance=None, **kwargs):
        # Python 3.14+ argparse colors --help on a TTY. Clak owns help color
        # (RichRecursiveHelpFormatter after wrap), so pin argparse color off.
        kwargs.setdefault("color", False)
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            kwargs.pop("color", None)
            super().__init__(*args, **kwargs)
        self.clak_instance = clak_instance

    def error(self, message):
        if getattr(self, "exit_on_error", True):
            return super().error(message)
        err = argparse.ArgumentError(None, message)
        err.clak_parser = self
        raise err

    def _supports_intermixed(self):
        """True when argparse intermixed parse can run on this parser.

        Subparsers (nargs=PARSER) and remainder positionals are incompatible.
        """
        for action in self._get_positional_actions():
            if action.nargs in (PARSER, REMAINDER):
                return False
        return True

    def _use_intermixed(self):
        """True when Meta.parse_intermixed is on and this parser can intermix."""
        inst = self.clak_instance
        if inst is None:
            return False
        if not inst.query_cfg_parents(
            "parse_intermixed", default=True, include_self=True
        ):
            return False
        return self._supports_intermixed()

    def parse_known_args(self, args=None, namespace=None):
        # Python 3.12+ raises ArgumentError from _parse_known_args (missing
        # required args, invalid choice) without calling error(). Stamp this
        # parser so nested failures keep leaf usage. Inner (child) stamps win.
        # Meta.parse_intermixed (default True) uses parse_known_intermixed_args
        # on leaves (no subparsers / remainder); parents with Command children
        # skip it. Set False to restore argparse leftover errors after a flag.
        try:
            if self._use_intermixed():
                return super().parse_known_intermixed_args(args, namespace)
            return super().parse_known_args(args, namespace)
        except argparse.ArgumentError as err:
            if getattr(err, "clak_parser", None) is None:
                err.clak_parser = self
            raise

    def parse_args(self, args=None, namespace=None):
        parsed, argv = self.parse_known_args(args, namespace)
        if argv:
            msg = _("unrecognized arguments: %s") % " ".join(argv)
            if self.exit_on_error:
                self.error(msg)
            err = argparse.ArgumentError(None, msg)
            leaf = getattr(parsed, "__cli_self__", None)
            err.clak_parser = getattr(leaf, "parser", None) or self
            raise err
        return parsed
