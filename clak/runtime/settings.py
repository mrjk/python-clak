"Common clak settings"

import logging
import os
import sys

from clak._optional import available, install_hint, optional
from clak.common import resolve_bool_option, to_boolean
from clak.exception import ClakUserError
from clak.runtime.log_levels import CLAK_CUSTOM_LEVEL_STYLES, register_clak_log_levels

COLOR_BACKENDS = frozenset({"none", "rich", "auto"})
CLAK_COLOR_BACKEND_ENV = "CLAK_COLOR_BACKEND"
DEFAULT_COLOR_BACKEND = "auto"

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
    return available("rich")


def color_backend_uses_rich(value=None) -> bool:
    """Whether Rich should be used for optional color/markup.

    * ``none``: never.
    * ``rich``: yes; missing package raises ClakUserError.
    * ``auto``: yes when rich is importable.
    """
    backend = resolve_color_backend(value)
    if backend == "none":
        return False
    rich_ok = _rich_importable()
    if backend == "rich":
        if not rich_ok:
            raise ClakUserError(
                "CLAK_COLOR_BACKEND=rich requires the rich package",
                advice=f"Install with: {install_hint('rich')}",
            )
        return True
    return rich_ok


class ClakSettings:
    """Process-level debug / color / log-format settings.

    ``from_env()`` reads ``CLAK_*`` at call time. ``current()`` returns the
    process settings, built once from the environment; ``set_current()``
    replaces them (tests, embedding apps) and ``replace()`` derives a copy.
    """

    _current: "ClakSettings | None" = None

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
        """Process settings (built from the environment on first use)."""
        if cls._current is None:
            cls._current = cls.from_env()
        return cls._current

    @classmethod
    def set_current(cls, settings: "ClakSettings | None") -> "ClakSettings | None":
        """Replace the process settings; None re-reads the env on next use.

        Returns the previous value so callers can restore it.
        """
        previous = cls._current
        cls._current = settings
        return previous

    def replace(self, **changes) -> "ClakSettings":
        """Return a copy with *changes* applied (``colors=False``, ...)."""
        return type(self)(**{**vars(self), **changes})

    def apply_debug_logging(self) -> None:
        """Enable debug logging once when ``debug`` is true (not at import)."""
        # pylint: disable=global-statement
        global _DEBUG_LOGGING_APPLIED
        if _DEBUG_LOGGING_APPLIED or not self.debug:
            return
        _DEBUG_LOGGING_APPLIED = True

        register_clak_log_levels()

        if self.colors:
            coloredlogs = optional("coloredlogs")
            if coloredlogs is not None:
                apply_coloredlogs_defaults(coloredlogs)
                coloredlogs.install(level="DEBUG")
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


def colors_enabled(*, clak_colors=None, env=None) -> bool:
    """Global color kill switches shared by help, logs, views and runtime.

    False when ``NO_COLOR`` is set and non-empty (https://no-color.org) or
    ``CLAK_COLORS`` is false. *clak_colors* overrides the process
    ``CLAK_COLORS`` value (e.g. one captured on a dispatch context).
    Per-surface rules (TTY, explicit flags, backend) build on top.
    """
    env = os.environ if env is None else env
    if env.get("NO_COLOR"):
        return False
    if clak_colors is None:
        clak_colors = ClakSettings.current().colors
    return bool(clak_colors)


def stream_isatty(stream) -> bool:
    """``stream.isatty()`` that tolerates missing, closed or fake streams."""
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def resolve_log_colors(cli_value=None, stream=None, env_value=_UNSET):
    """Resolve whether colored logs should be enabled.

    Precedence:
    1. Explicit CLI ``--log-colors`` / ``--no-log-colors`` (``cli_value`` not None)
    2. ``env_value`` when not omitted (default: ``ClakSettings.current().log_colors``,
       i.e. ``CLAK_LOG_COLORS``); ``None`` means unset
    3. Auto: :func:`colors_enabled` and ``stream.isatty()`` (default: stderr)
    """
    if stream is None:
        stream = sys.stderr
    if env_value is _UNSET:
        env_value = ClakSettings.current().log_colors
    return resolve_bool_option(
        cli_value,
        env_value=env_value,
        auto=lambda: colors_enabled() and stream_isatty(stream),
    )


def apply_coloredlogs_defaults(coloredlogs_module):
    """Apply Clak ``LOG_STYLES`` / ``LOG_FORMAT`` to a coloredlogs module."""
    coloredlogs_module.DEFAULT_LEVEL_STYLES = LOG_STYLES
    coloredlogs_module.DEFAULT_LOG_FORMAT = LOG_FORMAT


def apply_debug_logging(settings=None):
    """Enable debug logging from *settings* or ``ClakSettings.current()``."""
    (settings or ClakSettings.current()).apply_debug_logging()
