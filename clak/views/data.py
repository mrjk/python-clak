"""Data view: dump arbitrary payloads as JSON or YAML."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import json

from clak._optional import available, require
from clak.common import resolve_bool_option
from clak.exception import ClakUserError
from clak.runtime.rich_style import make_rich_console, syntax_kwargs
from clak.runtime.settings import colors_enabled, resolve_color_backend
from clak.views.base import ClakView
from clak.views.table_formatter import require_yaml

DATA_FORMATS = frozenset({"json", "yaml"})


def require_rich_for_data():
    """Import rich syntax helpers or raise ClakUserError."""
    purpose = "Colored data output"
    return require("rich.console", purpose), require("rich.syntax", purpose)


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


def _yaml_dumper(yaml, *, anchors: bool):
    """Return a SafeDumper, optionally disabling anchors/aliases."""
    if anchors:
        return yaml.SafeDumper

    class _NoAliasDumper(yaml.SafeDumper):
        def ignore_aliases(self, _data):  # pylint: disable=unused-argument
            """Always expand aliases instead of emitting anchors."""
            return True

    return _NoAliasDumper


def format_data_payload(payload, *, fmt=None, compact=False, anchors=True):
    """Serialize *payload* as JSON or YAML text (no color)."""
    resolved = resolve_data_format(fmt)

    if resolved == "json":
        indent = None if compact else 2
        text = json.dumps(payload, indent=indent, default=str)
        if not text.endswith("\n"):
            text += "\n"
        return text, resolved

    yaml = require_yaml()
    dumper = _yaml_dumper(yaml, anchors=bool(anchors))
    text = yaml.dump(
        payload,
        Dumper=dumper,
        sort_keys=False,
        default_flow_style=False,
    )
    return text, resolved


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

    if color is True:
        rich_console, rich_syntax = require_rich_for_data()
    else:
        try:
            rich_console, rich_syntax = require_rich_for_data()
        except ClakUserError:
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

    def render(self, *args, stdout=True, **kwargs):
        "Render data"

        payload, settings = self._render(*args, **kwargs)
        compact = bool(settings.pop("compact", False))
        anchors = settings.pop("anchors", True)
        if anchors is None:
            anchors = True
        else:
            anchors = bool(anchors)
        fmt_setting = settings.pop("format", None)
        color = settings.pop("color", None)
        stdout_tty = settings.get("stdout_tty")
        theme = self.settings.get("theme") or settings.pop("theme", None)

        text, fmt = format_data_payload(
            payload,
            fmt=fmt_setting,
            compact=compact,
            anchors=anchors,
        )
        rendered = colorize_data_text(
            text,
            fmt,
            color=color,
            stdout_tty=stdout_tty,
            theme=theme,
            clak_colors=settings.pop("clak_colors", None),
        )
        return self._output(rendered, stdout=stdout)
