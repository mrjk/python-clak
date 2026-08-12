"""Base view class and shared width / settings helpers."""

from __future__ import annotations

import logging
import textwrap
from collections.abc import Mapping
from pprint import pformat
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

OUTPUT_FORMATS = frozenset({"view", "yaml", "json", "csv"})
TEXT_FORMATS = frozenset({"view", "raw"})
WIDTH_MODES = frozenset({"content", "fit", "terminal"})
WIDTH_MODE_ALIASES = {
    "min": "content",
    "auto": "fit",
}
DEFAULT_WIDTH_MODE = "terminal"
DEFAULT_LINE_LENGTH = 120
LINE_LENGTH_KEYWORDS = frozenset({"terminal", "nowrap"})
WRAP_MODES = frozenset({"last", "all", "first"})
DEFAULT_WRAP_MODE = "last"
FORMAT_SCOPES = frozenset({"first", "all"})
DEFAULT_FORMAT_SCOPE = "first"


class ClakView:
    "Render command line output"

    settings_default = {}

    def __init__(self, payload=None, **kwargs):
        self.settings = kwargs or {}
        self.payload = payload

    def _render(self, *args, **settings):
        "Render data"

        # Fetch best payload
        if len(args) > 0:
            payload = args[0]
        else:
            payload = self.payload

        # Process settings
        _settings = dict(self.settings_default)
        _settings.update(self.settings)
        _settings.update(settings)

        return payload, _settings

    @staticmethod
    def _output(rendered, stdout=True):
        "Optionally print rendered output and always return it."
        if stdout:
            print(rendered)
        return rendered


def merge_view_settings(existing=None, cli_settings=None):
    """Merge CLI view settings over existing view settings.

    CLI values win. When CLI overrides a non-None existing value, log a warning.
    """
    existing = dict(existing or {})
    cli_settings = dict(cli_settings or {})
    merged = dict(existing)
    for key, cli_val in cli_settings.items():
        old_val = existing.get(key, None)
        if old_val is not None and old_val != cli_val:
            logger.warning(
                "CLI option %s=%r overrides view setting %r",
                key,
                cli_val,
                old_val,
            )
        merged[key] = cli_val
    return merged


def normalize_width_mode(mode: Optional[str] = None) -> str:
    """Return a canonical table width mode (``content`` / ``fit`` / ``terminal``).

    Accepts aliases ``min`` -> ``content`` and ``auto`` -> ``fit``.
    """
    if mode is None:
        return DEFAULT_WIDTH_MODE
    if not isinstance(mode, str):
        raise TypeError(f"width must be a string, got {type(mode).__name__}")
    key = mode.lower()
    key = WIDTH_MODE_ALIASES.get(key, key)
    if key not in WIDTH_MODES:
        raise ValueError(f"width must be one of {sorted(WIDTH_MODES)}, got {mode!r}")
    return key


def parse_line_length(value: Any = None):
    """Parse a text ``line_length``: positive int, ``terminal``, or ``nowrap``.

    ``0`` is rejected; use ``nowrap`` or ``terminal``.
    """
    if value is None:
        return DEFAULT_LINE_LENGTH
    if isinstance(value, bool):
        raise TypeError("line_length must be an int, 'terminal', or 'nowrap'")
    if isinstance(value, int):
        if value <= 0:
            raise ValueError("line_length must be > 0, 'terminal', or 'nowrap' (not 0)")
        return value
    if isinstance(value, str):
        lowered = value.lower().strip()
        if lowered in LINE_LENGTH_KEYWORDS:
            return lowered
        try:
            parsed = int(lowered)
        except ValueError as err:
            raise ValueError(
                "line_length must be a positive int, 'terminal', or 'nowrap'"
            ) from err
        if parsed <= 0:
            raise ValueError("line_length must be > 0, 'terminal', or 'nowrap' (not 0)")
        return parsed
    raise TypeError(
        "line_length must be an int, 'terminal', or 'nowrap', "
        f"got {type(value).__name__}"
    )


def resolve_view_width(
    settings: Optional[Mapping[str, Any]] = None,
    *,
    width: Optional[str] = None,
    term_width: Optional[int] = None,
    stdout_tty: Optional[bool] = None,
) -> Tuple[str, Optional[int]]:
    """Resolve effective table width mode and optional terminal budget.

    Non-TTY stdout forces ``fit`` / ``terminal`` down to ``content`` (no wrap).
    Returns ``(effective_mode, term_budget_or_none)``.
    """
    settings = dict(settings or {})
    if width is None:
        width = settings.get("width", DEFAULT_WIDTH_MODE)
    if term_width is None:
        term_width = settings.get("term_width")
    if stdout_tty is None:
        stdout_tty = settings.get("stdout_tty")

    mode = normalize_width_mode(width if width is not None else DEFAULT_WIDTH_MODE)

    if mode != "content" and not stdout_tty:
        mode = "content"

    if mode == "content":
        return mode, None

    if term_width is None:
        return "content", None

    return mode, int(term_width)


def resolve_line_length(
    settings: Optional[Mapping[str, Any]] = None,
    *,
    line_length: Any = None,
    term_width: Optional[int] = None,
    stdout_tty: Optional[bool] = None,
) -> Tuple[bool, Optional[int]]:
    """Resolve whether to wrap text and the column budget.

    ``nowrap`` or non-TTY stdout: no wrap. ``terminal``: wrap to ``term_width``.
    A positive int N: wrap to ``min(term_width, N)``.
    Returns ``(wrap, budget_or_none)``.
    """
    settings = dict(settings or {})
    if line_length is None:
        line_length = settings.get("line_length", DEFAULT_LINE_LENGTH)
    if term_width is None:
        term_width = settings.get("term_width")
    if stdout_tty is None:
        stdout_tty = settings.get("stdout_tty")

    parsed = parse_line_length(
        line_length if line_length is not None else DEFAULT_LINE_LENGTH
    )

    if parsed == "nowrap" or not stdout_tty:
        return False, None

    if term_width is None:
        return False, None

    term = int(term_width)
    if parsed == "terminal":
        return True, term
    return True, min(term, int(parsed))


def pformat_truncated(data, line_length=None, term_width=None, stdout_tty=None, **_):
    """Pretty-print *data*, optionally wrapping to the resolved line length."""
    wrap, budget = resolve_line_length(
        line_length=line_length if line_length is not None else DEFAULT_LINE_LENGTH,
        term_width=term_width,
        stdout_tty=stdout_tty,
    )
    if not wrap or budget is None:
        return pformat(data)

    formatted = pformat(data, width=budget)
    return textwrap.fill(formatted, width=budget)
