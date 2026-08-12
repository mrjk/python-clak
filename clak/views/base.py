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
WIDTH_MODES = frozenset({"min", "auto", "terminal"})
DEFAULT_WIDTH_MODE = "terminal"
WRAP_MODES = frozenset({"last", "all"})
DEFAULT_WRAP_MODE = "last"


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


def resolve_view_width(
    settings: Optional[Mapping[str, Any]] = None,
    *,
    width: Optional[str] = None,
    term_width: Optional[int] = None,
    stdout_tty: Optional[bool] = None,
) -> Tuple[str, Optional[int]]:
    """Resolve effective width mode and optional terminal budget.

    Non-TTY stdout forces ``auto`` / ``terminal`` down to ``min`` (no wrap).
    Returns ``(effective_mode, term_budget_or_none)``.
    """
    settings = dict(settings or {})
    if width is None:
        width = settings.get("width", DEFAULT_WIDTH_MODE)
    if term_width is None:
        term_width = settings.get("term_width")
    if stdout_tty is None:
        stdout_tty = settings.get("stdout_tty")

    mode = width if width is not None else DEFAULT_WIDTH_MODE
    if not isinstance(mode, str):
        raise TypeError(f"width must be a string, got {type(mode).__name__}")
    mode = mode.lower()
    if mode not in WIDTH_MODES:
        raise ValueError(f"width must be one of {sorted(WIDTH_MODES)}, got {mode!r}")

    if mode != "min" and not stdout_tty:
        mode = "min"

    if mode == "min":
        return mode, None

    if term_width is None:
        return "min", None

    return mode, int(term_width)


def pformat_truncated(data, width=None, term_width=None, stdout_tty=None, **_):
    """Pretty-print *data*, optionally wrapping to the resolved view width."""
    mode, term_budget = resolve_view_width(
        width=width if width is not None else DEFAULT_WIDTH_MODE,
        term_width=term_width,
        stdout_tty=stdout_tty,
    )
    if mode == "min" or term_budget is None:
        return pformat(data)

    formatted = pformat(data, width=term_budget)
    return textwrap.fill(formatted, width=term_budget)
