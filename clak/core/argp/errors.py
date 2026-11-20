"""Stable parse-error strings from argparse.ArgumentError."""

from __future__ import annotations

import argparse
from gettext import gettext as _


def _quoted(items) -> str:
    return ", ".join(repr(item) for item in items)


def format_argument_error(err: argparse.ArgumentError) -> str:
    """Build a Clak parse-error message.

    ``argument_name`` is often ``None`` (e.g. missing required args).
    Avoid embedding the literal ``None`` in user-facing output.
    """
    parts = [str(part) for part in (err.argument_name, err.message) if part]
    detail = " ".join(parts) if parts else str(err)
    return f"Could not parse command line: {detail}"


def invalid_choice_message(value, choices) -> str:
    """Always-quoted choice list (Python 3.12 stdlib omits quotes)."""
    return f"invalid choice: {value!r} (choose from {_quoted(choices)})"


def unknown_command_message(value, choices, suggestions=()) -> str:
    """Unknown subcommand, without the internal ``__cli_cmd__N`` dest."""
    msg = f"unknown command {value!r} (choose from {_quoted(choices)})"
    if suggestions:
        msg += f"; did you mean {_quoted(suggestions)}?"
    return msg


def ambiguous_command_message(value, matches) -> str:
    """Prefix matches several commands."""
    return f"ambiguous command {value!r} (could be {_quoted(matches)})"


def unrecognized_arguments_message(argv) -> str:
    """Stdlib wording (translated through argparse's gettext domain)."""
    return _("unrecognized arguments: %s") % " ".join(argv)
