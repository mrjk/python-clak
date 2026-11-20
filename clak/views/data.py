"""Data view: dump arbitrary payloads as JSON or YAML."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

from clak._optional import available, require
from clak.common import resolve_bool_option
from clak.exception import ClakUserError
from clak.runtime.rich_style import make_rich_console, syntax_kwargs
from clak.runtime.settings import colors_enabled, resolve_color_backend
from clak.views.base import ClakView
from clak.views.serialize import dump_json, dump_yaml, require_yaml

DATA_FORMATS = frozenset({"json", "yaml"})


def resolve_data_format(fmt=None) -> str:
    """Resolve ``json`` / ``yaml``; ``None`` / ``view`` means auto (yaml if available)."""
    if fmt is None or (isinstance(fmt, str) and fmt.lower() == "view"):
        return "yaml" if available("yaml") else "json"
    if not isinstance(fmt, str):
        raise TypeError(f"format must be a string, got {type(fmt).__name__}")
    fmt = fmt.lower()
    if fmt not in DATA_FORMATS:
        raise ValueError(
            f"Unsupported format {fmt!r}, choose one of: {sorted(DATA_FORMATS)}"
        )
    if fmt == "yaml":
        require_yaml()
    return fmt


def format_data_payload(payload, *, fmt=None, compact=False, anchors=True):
    """Serialize *payload* as JSON or YAML text (no color), newline-terminated."""
    resolved = resolve_data_format(fmt)
    if resolved == "json":
        return dump_json(payload, compact=compact) + "\n", resolved
    return dump_yaml(payload, anchors=bool(anchors)) + "\n", resolved


def colorize_data_text(
    text: str,
    language: str,
    *,
    color=None,
    stdout_tty=None,
    theme=None,
    **kwargs,
) -> str:
    """Optionally syntax-highlight *text* with rich.

    * ``color=True``: require rich and colorize (fails if missing).
    * ``color=False``: return plain text.
    * ``color=None`` (auto): colorize when CLAK_COLORS, TTY, and rich available.

    Syntax color is foreground-only (terminal background is left as-is).
    Theme: explicit *theme* > ``CLAK_SYNTAX_THEME`` > ``ansi_dark``.
    ``CLAK_COLOR_BACKEND=none`` skips Rich even when ``color=True``.
    """
    if resolve_color_backend() == "none":
        return text

    want_color = resolve_bool_option(
        color,
        auto=lambda: colors_enabled(clak_colors=kwargs.get("clak_colors"))
        and bool(stdout_tty),
    )
    if not want_color:
        return text

    try:
        rich_console = require("rich.console", "Colored data output")
        rich_syntax = require("rich.syntax", "Colored data output")
    except ClakUserError:
        if color is True:
            raise
        return text

    console = make_rich_console(rich_console)
    with console.capture() as capture:
        console.print(
            rich_syntax.Syntax(
                text.rstrip("\n"),
                language,
                word_wrap=False,
                **syntax_kwargs(theme),
            )
        )
    return capture.get().rstrip("\n")


class DataView(ClakView):
    """Render any payload as structured JSON or YAML."""

    settings_default = {
        "format": None,
        "compact": False,
        "color": None,
        "anchors": True,
        "theme": None,
    }

    instance_settings = ("theme",)

    def to_text(self, payload, settings):
        anchors = settings.get("anchors")
        text, fmt = format_data_payload(
            payload,
            fmt=settings.get("format"),
            compact=bool(settings.get("compact")),
            anchors=True if anchors is None else bool(anchors),
        )
        # No leading/trailing blank lines: the output adds its own final newline
        return colorize_data_text(
            text.strip("\n"),
            fmt,
            color=settings.get("color"),
            stdout_tty=settings.get("stdout_tty"),
            theme=settings.get("theme"),
            clak_colors=settings.get("clak_colors"),
        )
