"""Stable parse-error strings from argparse.ArgumentError."""

from __future__ import annotations

import argparse


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
    def unrecognized_arguments_message(argv) -> str:
        """Stdlib wording, with gettext left to the caller if needed."""
        return "unrecognized arguments: " + " ".join(argv)


_DEFAULT_RENDERER = ErrorRenderer()


def format_argument_error(err: argparse.ArgumentError) -> str:
    """Module-level helper used by Dispatcher."""
    return _DEFAULT_RENDERER.format_argument_error(err)
