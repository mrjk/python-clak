"""Base view class and shared width / settings helpers."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

import logging
import re
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
DEFAULT_WIDTH_MODE = "fit"
DEFAULT_LINE_LENGTH = 120
LINE_LENGTH_KEYWORDS = frozenset({"terminal", "nowrap"})
WRAP_MODES = frozenset({"last", "all", "first"})
DEFAULT_WRAP_MODE = "last"
FORMAT_SCOPES = frozenset({"first", "all"})
DEFAULT_FORMAT_SCOPE = "first"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes for width measurements."""
    return _ANSI_RE.sub("", text)


class ClakView:
    """Render command line output.

    Subclasses implement :meth:`to_text`; :meth:`render` merges settings
    (``settings_default`` < constructor kwargs < render kwargs), prints the
    text unless ``stdout=False``, and returns it. Keys listed in
    ``instance_settings`` keep a non-empty constructor value over render kwargs.
    """

    settings_default = {}
    instance_settings = ()

    def __init__(self, payload=None, **kwargs):
        self.settings = kwargs or {}
        self.payload = payload

    def render(self, *args, stdout=True, **settings):
        """Render ``args[0]`` (default: the constructor payload) as text."""
        payload = args[0] if args else self.payload
        merged = {**self.settings_default, **self.settings, **settings}
        for key in self.instance_settings:
            if self.settings.get(key):
                merged[key] = self.settings[key]
        rendered = self.to_text(payload, merged)
        if stdout:
            print(rendered)
        return rendered

    def to_text(self, payload, settings: dict) -> str:
        """Build the output text (*settings* is a fresh dict, safe to pop)."""
        raise NotImplementedError(f"{type(self).__name__} must implement to_text()")

    @staticmethod
    def merge_settings(existing=None, cli_settings=None):
        """Merge CLI view settings over existing view settings.

        CLI values win. When CLI overrides a non-None existing value, log at INFO.
        """
        existing = dict(existing or {})
        cli_settings = dict(cli_settings or {})
        merged = dict(existing)
        for key, cli_val in cli_settings.items():
            old_val = existing.get(key, None)
            if old_val is not None and old_val != cli_val:
                logger.info(
                    "CLI option %s=%r overrides view setting %r",
                    key,
                    cli_val,
                    old_val,
                )
            merged[key] = cli_val
        return merged


def render_result(data, leaf, view_settings: dict) -> None:
    """Print a ``cli_run`` result with the view that applies.

    A returned :class:`ClakView` renders itself (CLI view settings win over
    its own); otherwise *leaf*'s ``Meta.cli_view`` (instance or subclass), if
    any, renders *data*.
    """
    if isinstance(data, ClakView):
        data.render(**ClakView.merge_settings(data.settings, view_settings))
        return
    viewer = leaf.query_cfg_parents("cli_view", default=None)
    if isinstance(viewer, type) and issubclass(viewer, ClakView):
        viewer = viewer()
    if viewer is None:
        return
    if not isinstance(viewer, ClakView):
        raise TypeError("Meta.cli_view must be a ClakView instance or subclass")
    viewer.render(data, **view_settings)


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
        line_length=line_length, term_width=term_width, stdout_tty=stdout_tty
    )
    if not wrap or budget is None:
        return pformat(data)

    formatted = pformat(data, width=budget)
    return textwrap.fill(formatted, width=budget)
