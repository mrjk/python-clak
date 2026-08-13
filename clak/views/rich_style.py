"""Compatibility re-export; implementation lives in ``clak.runtime.rich_style``."""

from clak.runtime.rich_style import (
    CLAK_SYNTAX_THEME_ENV,
    DEFAULT_SYNTAX_THEME,
    make_rich_console,
    render_markup_text,
    resolve_syntax_theme,
    syntax_kwargs,
)

__all__ = [
    "CLAK_SYNTAX_THEME_ENV",
    "DEFAULT_SYNTAX_THEME",
    "make_rich_console",
    "render_markup_text",
    "resolve_syntax_theme",
    "syntax_kwargs",
]
