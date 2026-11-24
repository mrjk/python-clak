"""Optional help mixins: Rich-colored ``--help``, split short/long help."""

from clak.core.help_render import RichRecursiveHelpFormatter


class RichHelpMixin:  # pylint: disable=too-few-public-methods
    """Same default as ``Parser`` (Rich help formatter).

    Optional. Useful to re-opt-in a child after a parent sets
    ``Meta.help_formatter = RecursiveHelpFormatter``.
    """

    meta__help_formatter = RichRecursiveHelpFormatter


class LongHelpMixin:  # pylint: disable=too-few-public-methods
    """``-h`` prints the short help, ``--help`` the full one.

    Replaces ``--help-all`` and ``--help-<topic>``. Inherited by subcommands.
    """

    meta__help_split = True
