"Common clak settings"

import logging
import os
import sys

from clak.common import resolve_bool_option, to_boolean
from clak.exception import ClakUserError
from clak.runtime.log_levels import CLAK_CUSTOM_LEVEL_STYLES, register_clak_log_levels

COLOR_BACKENDS = frozenset({"none", "rich", "auto"})
CLAK_COLOR_BACKEND_ENV = "CLAK_COLOR_BACKEND"
DEFAULT_COLOR_BACKEND = "auto"
_RICH_INSTALL_HINT = "pip install 'mrjk.clak[markdown]'"

LOG_STYLES = {
    "debug": {"color": "magenta"},
    "info": {"color": "blue"},
    "warning": {"color": "yellow"},
    "error": {"color": "red"},
    "critical": {"color": "red", "bold": True},
    **CLAK_CUSTOM_LEVEL_STYLES,
}
LOG_FORMAT = "[%(levelname)8s] %(message)s"

# Sentinel so callers can pass ``env_value=None`` (unset) vs omit the arg.
_UNSET = object()
_DEBUG_LOGGING_APPLIED = False


def _normalize_color_backend(raw) -> str:
    """Return ``none`` / ``rich`` / ``auto``; empty means auto."""
    if raw is None:
        return DEFAULT_COLOR_BACKEND
    if not isinstance(raw, str):
        raise TypeError(f"color backend must be a string, got {type(raw).__name__}")
    key = raw.strip().lower()
    if not key:
        return DEFAULT_COLOR_BACKEND
    if key not in COLOR_BACKENDS:
        raise ValueError(
            f"CLAK_COLOR_BACKEND must be one of {sorted(COLOR_BACKENDS)}, got {raw!r}"
        )
    return key


def resolve_color_backend(value=None) -> str:
    """Resolve ``none`` / ``rich`` / ``auto``.

    Explicit *value* wins; otherwise ``CLAK_COLOR_BACKEND``; unset/empty is auto.
    """
    if value is not None:
        return _normalize_color_backend(value)
    return _normalize_color_backend(os.environ.get(CLAK_COLOR_BACKEND_ENV))


def _rich_importable() -> bool:
    try:
        import rich  # noqa: F401  # pylint: disable=import-outside-toplevel,unused-import
    except ImportError:
        return False
    return True


def color_backend_uses_rich(value=None) -> bool:
    """Whether Rich should be used for optional color/markup.

    * ``none``: never.
    * ``rich``: yes; missing package raises ClakUserError.
    * ``auto``: yes when rich is importable.
    """
    backend = resolve_color_backend(value)
    if backend == "none":
        return False
    available = _rich_importable()
    if backend == "rich":
        if not available:
            raise ClakUserError(
                "CLAK_COLOR_BACKEND=rich requires the rich package",
                advice=f"Install with: {_RICH_INSTALL_HINT}",
            )
        return True
    return available


class ClakSettings:
    """Process-level debug / color / log-format settings.

    ``from_env()`` reads ``CLAK_*`` at call time. ``current()`` prefers the
    module aliases (``CLAK_DEBUG``, ``CLAK_COLORS``, ``CLAK_LOG_COLORS``) so
    tests can still monkeypatch those names.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        debug: bool,
        colors: bool,
        color_backend: str,
        log_colors,
        styles: dict,
        log_format: str,
    ):
        self.debug = bool(debug)
        self.colors = bool(colors)
        self.color_backend = color_backend
        self.log_colors = log_colors
        self.styles = styles
        self.log_format = log_format

    @classmethod
    def from_env(cls) -> "ClakSettings":
        """Build settings from the current process environment."""
        raw_log_colors = os.environ.get("CLAK_LOG_COLORS")
        return cls(
            debug=to_boolean(os.environ.get("CLAK_DEBUG", False)),
            colors=to_boolean(os.environ.get("CLAK_COLORS", True)),
            color_backend=resolve_color_backend(),
            log_colors=(
                to_boolean(raw_log_colors) if raw_log_colors is not None else None
            ),
            styles=dict(LOG_STYLES),
            log_format=LOG_FORMAT,
        )

    @classmethod
    def current(cls) -> "ClakSettings":
        """Process defaults; module aliases win so tests can monkeypatch."""
        return cls(
            debug=bool(CLAK_DEBUG),
            colors=bool(CLAK_COLORS),
            color_backend=resolve_color_backend(),
            log_colors=CLAK_LOG_COLORS,
            styles=dict(LOG_STYLES),
            log_format=LOG_FORMAT,
        )

    def apply_debug_logging(self) -> None:
        """Enable debug logging once when ``debug`` is true (not at import)."""
        # pylint: disable=global-statement
        global _DEBUG_LOGGING_APPLIED
        if _DEBUG_LOGGING_APPLIED or not self.debug:
            return
        _DEBUG_LOGGING_APPLIED = True

        register_clak_log_levels()

        if self.colors:
            try:
                import coloredlogs  # pylint: disable=import-outside-toplevel

                apply_coloredlogs_defaults(coloredlogs)
                coloredlogs.install(level="DEBUG")
            except ImportError:
                pass
        else:
            logging.basicConfig(
                level=logging.DEBUG,
                format="[%(levelname)8s] %(name)s - %(message)s",
            )

        logging.getLogger().debug(
            "Debug logging enabled via CLAK_DEBUG=%s with CLAK_COLORS=%s",
            self.debug,
            self.colors,
        )


_PROCESS_SETTINGS = ClakSettings.from_env()
CLAK_DEBUG = _PROCESS_SETTINGS.debug
CLAK_COLORS = _PROCESS_SETTINGS.colors
CLAK_LOG_COLORS = _PROCESS_SETTINGS.log_colors


def resolve_log_colors(cli_value=None, stream=None, env_value=_UNSET):
    """Resolve whether colored logs should be enabled.

    Precedence:
    1. Explicit CLI ``--log-colors`` / ``--no-log-colors`` (``cli_value`` not None)
    2. ``env_value`` when not omitted (default: ``CLAK_LOG_COLORS``); ``None`` means unset
    3. Auto: ``CLAK_COLORS`` and ``stream.isatty()`` (default stream: stderr)
    """
    if stream is None:
        stream = sys.stderr
    if env_value is _UNSET:
        env_value = CLAK_LOG_COLORS
    return resolve_bool_option(
        cli_value,
        env_value=env_value,
        auto=lambda: bool(CLAK_COLORS) and stream.isatty(),
    )


def apply_coloredlogs_defaults(coloredlogs_module):
    """Apply Clak ``LOG_STYLES`` / ``LOG_FORMAT`` to a coloredlogs module."""
    coloredlogs_module.DEFAULT_LEVEL_STYLES = LOG_STYLES
    coloredlogs_module.DEFAULT_LOG_FORMAT = LOG_FORMAT


def apply_debug_logging(settings=None):
    """Enable debug logging from *settings* or ``ClakSettings.current()``."""
    (settings or ClakSettings.current()).apply_debug_logging()
