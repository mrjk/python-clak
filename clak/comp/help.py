"""Rich-colored ``--help`` (default formatter; opt out via Meta).

``RichRecursiveHelpFormatter`` is the Parser default marker for colored
help. Layout lives in ``HelpRenderer``. Color follows ``NO_COLOR``,
``CLAK_COLORS``, ``CLAK_COLOR_BACKEND``, TTY stdout, and whether Rich is
importable. Missing Rich degrades to plain HelpRenderer layout (no ANSI).
"""

from __future__ import annotations

import os
import sys

from clak.core.help_render import HelpDocument, RecursiveHelpFormatter
from clak.runtime.rich_style import make_rich_console, render_markup_text
from clak.runtime.settings import ClakSettings, color_backend_uses_rich

try:
    import rich.console as rich_console
    from rich.text import Text
except ImportError:
    rich_console = None
    Text = None

_HELP_STYLES = {
    "argparse.groups": "bold magenta",
    "argparse.args": "cyan",
    "argparse.cmds": "dark_cyan",
    "argparse.default": "dim",
}

_PART_STYLES = {
    "group": "argparse.groups",
    "args": "argparse.args",
    "cmds": "argparse.cmds",
    "default": "argparse.default",
}


class RichRecursiveHelpFormatter(RecursiveHelpFormatter):
    """Marker: same layout as ``RecursiveHelpFormatter``, with Rich color."""


def help_uses_rich() -> bool:
    """Whether ``--help`` should emit ANSI."""
    if os.environ.get("NO_COLOR"):
        return False
    if not ClakSettings.current().colors:
        return False
    if not sys.stdout.isatty():
        return False
    return color_backend_uses_rich()


def help_document_colorizer(document: HelpDocument) -> str:
    """Style a HelpDocument. No regex on argparse text."""
    if not help_uses_rich() or rich_console is None or Text is None:
        return document.to_plain()
    styled = Text()
    max_len = 80
    for line in document.lines:
        line_text = "".join(text for _kind, text in line.parts)
        max_len = max(max_len, len(line_text))
        for kind, chunk in line.parts:
            if kind == "markup":
                rendered = render_markup_text(chunk)
                if rendered != chunk and hasattr(Text, "from_ansi"):
                    styled.append_text(Text.from_ansi(rendered))
                elif rendered != chunk:
                    styled.append(rendered)
                else:
                    try:
                        styled.append_text(Text.from_markup(chunk))
                    except Exception:  # pylint: disable=broad-exception-caught
                        styled.append(chunk)
            else:
                style = _PART_STYLES.get(kind)
                if style:
                    styled.append(chunk, style=style)
                else:
                    styled.append(chunk)
        styled.append("\n")
    console = make_rich_console(
        rich_console, width=max(max_len, 80), theme=_HELP_STYLES
    )
    with console.capture() as capture:
        console.print(styled, end="", overflow="ignore", crop=False, highlight=False)
    return capture.get()


class RichHelpMixin:  # pylint: disable=too-few-public-methods
    """Same default as ``Parser`` (Rich help formatter).

    Optional. Useful to re-opt-in a child after a parent sets
    ``Meta.help_formatter = RecursiveHelpFormatter``.
    """

    meta__help_formatter = RichRecursiveHelpFormatter
