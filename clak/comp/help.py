"""Rich-colored ``--help`` (default formatter; opt out via Meta).

``RichRecursiveHelpFormatter`` is the Parser default. Color follows
``NO_COLOR``, ``CLAK_COLORS``, ``CLAK_COLOR_BACKEND``, TTY stdout, and
whether Rich is importable. Missing Rich degrades to plain
``RecursiveHelpFormatter`` layout (no ANSI).
"""

from __future__ import annotations

import os
import sys

from clak.core.argparse_ import RecursiveHelpFormatter
from clak.runtime.rich_style import make_rich_console, render_markup_text
from clak.runtime.settings import CLAK_COLORS, color_backend_uses_rich

try:
    import rich.console as rich_console
    from rich.highlighter import RegexHighlighter
    from rich.text import Text
except ImportError:
    rich_console = None
    RegexHighlighter = object
    Text = None

# Rich has no argparse keys in DEFAULT_STYLES. Groups use Rich's heading
# magenta (bold); args/cmds follow the usual cyan / dark_cyan argparse pair.
_HELP_STYLES = {
    "argparse.groups": "bold magenta",
    "argparse.args": "cyan",
    "argparse.cmds": "dark_cyan",
    "argparse.default": "dim",
}

# (?m) so section titles match after the first line. Flags only on option
# definition lines (not ``--flag`` in description/epilog prose). Left-column
# command / positional names (not wrapped help prose).
_HELP_HIGHLIGHTS = (
    r"(?m)^(?P<groups>usage:)",
    r"(?m)^(?P<groups>(?:positional arguments|options|subcommands):)",
    r"(?m)^(?P<groups>[A-Za-z][\w /()-]+:\s*$)",
    r"(?m)^\s+(?P<args>-{1,2}[\w-]+(?: [A-Z][A-Z0-9_]*)?"
    r"(?:, -{1,2}[\w-]+(?: [A-Z][A-Z0-9_]*)?)*)",
    r"(?m)^ {2,14}(?P<cmds>[\w][\w-]*(?: [\w][\w-]*)*)(?: {2,}|\s*$)",
    r"(?P<default>\(default: [^)]*\))",
)


class HelpHighlighter(RegexHighlighter):  # pylint: disable=too-few-public-methods
    """Highlight argparse help structure."""

    base_style = "argparse."
    highlights = list(_HELP_HIGHLIGHTS)


def help_uses_rich() -> bool:
    """Whether ``--help`` should emit ANSI."""
    if os.environ.get("NO_COLOR"):
        return False
    if not CLAK_COLORS:
        return False
    if not sys.stdout.isatty():
        return False
    return color_backend_uses_rich()


def _colorize_help(text: str, width: int) -> str:
    """Apply fg-only argparse styles without rewrapping *text*."""
    if rich_console is None or Text is None:
        return text
    lines = text.splitlines() or [""]
    console_width = max(width, max(len(line) for line in lines), 80)
    console = make_rich_console(rich_console, width=console_width, theme=_HELP_STYLES)
    styled = HelpHighlighter()(Text(text))
    with console.capture() as capture:
        console.print(styled, end="", overflow="ignore", crop=False, highlight=False)
    return capture.get()


class RichRecursiveHelpFormatter(RecursiveHelpFormatter):
    """``RecursiveHelpFormatter`` plus optional Rich color and markup.

    Layout (command tree, defaults, option invocation) stays in the parent.
    Color is applied after ``format_help()`` so wrapping is unchanged.
    """

    def _format_text(self, text):
        if text and help_uses_rich():
            text = render_markup_text(text)
        return super()._format_text(text)

    def format_help(self):
        text = super().format_help()
        if not help_uses_rich():
            return text
        return _colorize_help(text, width=self._width)


class RichHelpMixin:  # pylint: disable=too-few-public-methods
    """Same default as ``Parser`` (Rich help formatter).

    Optional. Useful to re-opt-in a child after a parent sets
    ``Meta.help_formatter = RecursiveHelpFormatter``.
    """

    meta__help_formatter = RichRecursiveHelpFormatter
