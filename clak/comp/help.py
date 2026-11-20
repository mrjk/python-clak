"""Optional mixin re-enabling the Rich-colored ``--help`` (Parser default)."""

from clak.core.help_render import RichRecursiveHelpFormatter


class RichHelpMixin:  # pylint: disable=too-few-public-methods
    """Same default as ``Parser`` (Rich help formatter).

    Optional. Useful to re-opt-in a child after a parent sets
    ``Meta.help_formatter = RecursiveHelpFormatter``.
    """

    meta__help_formatter = RichRecursiveHelpFormatter
