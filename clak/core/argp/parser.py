"""Stable ArgumentParser across Python 3.10-3.14."""

from __future__ import annotations

import argparse
import difflib

from clak.core.argp import errors
from clak.core.argp.actions import SubParsersAction
from clak.core.argp.capabilities import ArgparseCapabilities


class ArgumentParser(argparse.ArgumentParser):
    """Argparse adapter with Clak-stable parse and error behavior.

    Does not import ParserNode. The owner sets ``parse_intermixed`` and
    optional ``clak_help_renderer`` (duck-typed ``format_help``).
    ``format_usage`` stays stdlib argparse (uncolored ``usage:`` prefix).
    """

    def __init__(
        self,
        *args,
        clak_instance=None,
        parse_intermixed=True,
        capabilities=None,
        **kwargs,
    ):
        self.capabilities = capabilities or ArgparseCapabilities.detect()
        if self.capabilities.has_color_kwarg:
            kwargs.setdefault("color", False)
        else:
            kwargs.pop("color", None)
        super().__init__(*args, **kwargs)
        self.clak_instance = clak_instance
        self.parse_intermixed = parse_intermixed
        self._intermixed_reentrant = False
        self.clak_help_renderer = None

    def format_help(self):
        renderer = self.clak_help_renderer
        if renderer is not None:
            return renderer.format_help()
        return super().format_help()

    def error(self, message):
        if getattr(self, "exit_on_error", True):
            return super().error(message)
        err = argparse.ArgumentError(None, message)
        err.clak_parser = self
        raise err

    def _check_value(self, action, value):
        if isinstance(action, SubParsersAction):
            self._check_command(action, value)
            return
        if action.choices is not None and value not in action.choices:
            msg = errors.invalid_choice_message(value, action.choices)
            raise argparse.ArgumentError(action, msg)

    def _check_command(self, action, value):
        """Validate a subcommand name; the action expands a unique prefix.

        Errors use ``ArgumentError(None, ...)`` so the internal
        ``__cli_cmd__N`` dest never reaches the user.
        """
        if action.resolve(value) is not None:
            return
        names = action.command_names()
        if action.allow_abbrev:
            matches = action.prefix_matches(value) if value else []
            if len(matches) > 1:
                raise argparse.ArgumentError(
                    None, errors.ambiguous_command_message(value, matches)
                )
        suggestions = [name for name in names if value and name.startswith(value)]
        for name in difflib.get_close_matches(value, names, n=3, cutoff=0.75):
            if name not in suggestions:
                suggestions.append(name)
        raise argparse.ArgumentError(
            None,
            errors.unknown_command_message(value, names, suggestions[:3]),
        )

    def _supports_intermixed(self):
        """True when argparse intermixed parse can run on this parser.

        Subparsers (nargs=PARSER) and remainder positionals are incompatible.
        """
        for action in self._get_positional_actions():
            if action.nargs in (argparse.PARSER, argparse.REMAINDER):
                return False
        return True

    def _use_intermixed(self):
        """True when the owner enabled intermixed and this parser can run it.

        Python 3.10-3.11 parse_known_intermixed_args calls parse_known_args
        twice. Those reentrant calls must use standard parse, not intermixed.
        """
        if self.capabilities.intermixed_reenters and self._intermixed_reentrant:
            return False
        if not self.parse_intermixed:
            return False
        return self._supports_intermixed()

    def parse_known_args(self, args=None, namespace=None):
        try:
            if self._use_intermixed():
                self._intermixed_reentrant = True
                try:
                    return super().parse_known_intermixed_args(args, namespace)
                finally:
                    self._intermixed_reentrant = False
            return super().parse_known_args(args, namespace)
        except argparse.ArgumentError as err:
            if getattr(err, "clak_parser", None) is None:
                err.clak_parser = self
            raise

    def parse_args(self, args=None, namespace=None):
        parsed, argv = self.parse_known_args(args, namespace)
        if argv:
            msg = errors.unrecognized_arguments_message(argv)
            if self.exit_on_error:
                self.error(msg)
            err = argparse.ArgumentError(None, msg)
            leaf = getattr(parsed, "__cli_self__", None)
            err.clak_parser = getattr(leaf, "parser", None) or self
            raise err
        return parsed
