"""Shared Rich console and Syntax theme helpers (fg-only terminal color)."""

from __future__ import annotations

import os

from clak.runtime.settings import color_backend_uses_rich

DEFAULT_SYNTAX_THEME = "ansi_dark"
CLAK_SYNTAX_THEME_ENV = "CLAK_SYNTAX_THEME"

_MARKDOWN_FG_STYLES = {
    "markdown.code": "bold cyan",
    "markdown.code_block": "cyan",
}


def resolve_syntax_theme(theme=None) -> str:
    """Resolve a Pygments/Rich Syntax theme name.

    Priority: explicit *theme* > ``CLAK_SYNTAX_THEME`` > ``ansi_dark``.
    Empty or whitespace values fall through to the next source.
    """
    if theme is not None:
        if not isinstance(theme, str):
            raise TypeError(f"theme must be a string, got {type(theme).__name__}")
        stripped = theme.strip()
        if stripped:
            return stripped
    env = os.environ.get(CLAK_SYNTAX_THEME_ENV)
    if env is not None:
        stripped = env.strip()
        if stripped:
            return stripped
    return DEFAULT_SYNTAX_THEME


def syntax_kwargs(theme=None) -> dict:
    """Keyword args for ``rich.syntax.Syntax``: fg-only, resolved theme."""
    return {
        "theme": resolve_syntax_theme(theme),
        "background_color": "default",
    }


def make_rich_console(rich_console, *, width=None, theme=None):
    """Build a capture-friendly Console with fg-only markdown code styles.

    Auto-detects color depth; falls back to truecolor when detection yields
    none (dumb TERM / pytest capture) because the caller already opted in.

    *theme* is a style dict or a Rich ``Theme``. Default is markdown code
    fg styles.
    """
    from rich.theme import Theme  # pylint: disable=import-outside-toplevel

    if theme is None:
        resolved_theme = Theme(_MARKDOWN_FG_STYLES)
    elif isinstance(theme, dict):
        resolved_theme = Theme(theme)
    else:
        resolved_theme = theme
    console_kwargs = {
        "force_terminal": True,
        "highlight": False,
        "soft_wrap": True,
        "no_color": False,
        "theme": resolved_theme,
    }
    if width is not None:
        console_kwargs["width"] = width
    console = rich_console.Console(**console_kwargs)
    if console.color_system is None:
        console = rich_console.Console(**console_kwargs, color_system="truecolor")
    return console


def render_markup_text(text: str) -> str:
    """Render Rich markup to ANSI, or return *text* unchanged when Rich is off."""
    if not text or not color_backend_uses_rich():
        return text
    import rich.console as rich_console  # pylint: disable=import-outside-toplevel

    console = make_rich_console(rich_console)
    with console.capture() as capture:
        console.print(text, markup=True, highlight=False)
    return capture.get().rstrip("\n")
