"""Stable parse-error strings from argparse.ArgumentError."""

from __future__ import annotations

import argparse
from gettext import gettext as _


class ErrorRenderer:
    """Format argparse parse failures without regex on stdlib text."""

    def format_argument_error(self, err: argparse.ArgumentError) -> str:
        """Build a Clak parse-error message.

        ``argument_name`` is often ``None`` (e.g. missing required args).
        Avoid embedding the literal ``None`` in user-facing output.
        """
        parts = []
        if err.argument_name:
            parts.append(str(err.argument_name))
        if err.message:
            parts.append(str(err.message))
        detail = " ".join(parts) if parts else str(err)
        return f"Could not parse command line: {detail}"

    @staticmethod
    def invalid_choice_message(value, choices) -> str:
        """Always-quoted choice list (Python 3.12 stdlib omits quotes)."""
        listed = ", ".join(repr(item) for item in choices)
        return f"invalid choice: {value!r} (choose from {listed})"

    @staticmethod
    def unknown_command_message(value, choices, suggestions=()) -> str:
        """Unknown subcommand, without the internal ``__cli_cmd__N`` dest."""
        listed = ", ".join(repr(item) for item in choices)
        msg = f"unknown command {value!r} (choose from {listed})"
        if suggestions:
            hint = ", ".join(repr(item) for item in suggestions)
            msg += f"; did you mean {hint}?"
        return msg

    @staticmethod
    def ambiguous_command_message(value, matches) -> str:
        """Prefix matches several commands."""
        listed = ", ".join(repr(item) for item in matches)
        return f"ambiguous command {value!r} (could be {listed})"

    @staticmethod
    def unrecognized_arguments_message(argv) -> str:
        """Stdlib wording (translated through argparse's gettext domain)."""
        return _("unrecognized arguments: %s") % " ".join(argv)


_DEFAULT_RENDERER = ErrorRenderer()


def format_argument_error(err: argparse.ArgumentError) -> str:
    """Module-level helper used by Dispatcher."""
    return _DEFAULT_RENDERER.format_argument_error(err)
