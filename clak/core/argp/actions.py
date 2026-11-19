"""Subcommand action with optional unique-prefix matching."""

from __future__ import annotations

import argparse


# pylint: disable-next=protected-access
class SubParsersAction(argparse._SubParsersAction):
    """``add_subparsers`` action that can expand unambiguous command prefixes.

    With ``allow_abbrev`` on, ``app sub bu`` runs ``app sub buzz`` when
    ``buzz`` is the only command (or alias of one command) starting with
    ``bu``. An exact name always wins, so ``sub`` still selects ``sub`` when
    ``subx`` also exists. The owner may flip ``allow_abbrev`` after build.
    """

    def __init__(self, *args, allow_abbrev=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_abbrev = allow_abbrev

    def command_names(self):
        """All accepted command names, aliases included, in declare order."""
        return list(self._name_parser_map)

    def prefix_matches(self, value):
        """Command names starting with ``value`` (aliases of one parser deduped).

        Returns a list of names, one per distinct target parser.
        """
        seen = []
        names = []
        for name, parser in self._name_parser_map.items():
            if name.startswith(value) and not any(parser is p for p in seen):
                seen.append(parser)
                names.append(name)
        return names

    def resolve(self, value):
        """Return the full command name for ``value``, or None.

        None means unknown (or abbreviation disabled). Ambiguity is reported
        by :meth:`prefix_matches` returning more than one name; this method
        returns None for that case too.
        """
        if value in self._name_parser_map:
            return value
        if not self.allow_abbrev or not value:
            return None
        matches = self.prefix_matches(value)
        if len(matches) == 1:
            return matches[0]
        return None

    def __call__(self, parser, namespace, values, option_string=None):
        resolved = self.resolve(values[0])
        if resolved is not None and resolved != values[0]:
            values = [resolved] + list(values[1:])
        super().__call__(parser, namespace, values, option_string)
