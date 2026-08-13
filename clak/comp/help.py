"""Optional Rich-colored ``--help``.

``RichHelpMixin`` swaps the argparse formatter. No CLI flags. Color follows
``CLAK_COLORS``, ``CLAK_COLOR_BACKEND``, TTY stdout, and whether Rich is
importable. Missing Rich degrades to plain ``RecursiveHelpFormatter`` output.
"""

from __future__ import annotations

import sys

from clak.core.argparse_ import RecursiveHelpFormatter
from clak.runtime.rich_style import render_markup_text
from clak.runtime.settings import CLAK_COLORS, color_backend_uses_rich

try:
    import rich.console as rich_console
    from rich.highlighter import RegexHighlighter
    from rich.text import Text
    from rich.theme import Theme
except ImportError:
    rich_console = None
    RegexHighlighter = object
    Text = None
    Theme = None

_HELP_STYLES = {
    "argparse.groups": "bold",
    "argparse.args": "cyan",
    "argparse.default": "dim",
}

# (?m) so section titles match after the first line. Flags only on option
# definition lines (not ``--flag`` in description/epilog prose).
_HELP_HIGHLIGHTS = (
    r"(?m)^(?P<groups>usage:)",
    r"(?m)^(?P<groups>(?:positional arguments|options|subcommands):)",
    r"(?m)^(?P<groups>[A-Za-z][\w /-]+:\s*$)",
    r"(?m)^\s+(?P<args>-{1,2}[\w-]+(?: [A-Z][A-Z0-9_]*)?"
    r"(?:, -{1,2}[\w-]+(?: [A-Z][A-Z0-9_]*)?)*)",
    r"(?P<default>\(default: [^)]*\))",
)


class HelpHighlighter(RegexHighlighter):  # pylint: disable=too-few-public-methods
    """Highlight argparse help structure."""

    base_style = "argparse."
    highlights = list(_HELP_HIGHLIGHTS)


def help_uses_rich() -> bool:
    """Whether ``--help`` should emit ANSI (mixin formatter calls this)."""
    if not CLAK_COLORS:
        return False
    if not sys.stdout.isatty():
        return False
    return color_backend_uses_rich()


def _colorize_help(text: str, width: int) -> str:
    """Apply fg-only argparse styles without rewrapping *text*."""
    if rich_console is None or Text is None or Theme is None:
        return text
    lines = text.splitlines() or [""]
    console_width = max(width, max(len(line) for line in lines), 80)
    console = rich_console.Console(
        force_terminal=True,
        color_system="truecolor",
        width=console_width,
        highlight=False,
        soft_wrap=True,
        no_color=False,
        theme=Theme(_HELP_STYLES),
    )
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
    """Opt-in Rich ``--help``. Put left of ``Parser``. No CLI flags."""

    meta__help_formatter = RichRecursiveHelpFormatter
