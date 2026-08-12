"Common clak settings"

import os
import sys

from clak.common import resolve_bool_option, to_boolean
from clak.runtime.log_levels import CLAK_CUSTOM_LEVEL_STYLES, register_clak_log_levels

CLAK_DEBUG = to_boolean(os.environ.get("CLAK_DEBUG", False))
CLAK_COLORS = to_boolean(os.environ.get("CLAK_COLORS", True))

# Optional override for ``--log-colors`` default. Unset means "auto".
_CLAK_LOG_COLORS_RAW = os.environ.get("CLAK_LOG_COLORS")
CLAK_LOG_COLORS = (
    to_boolean(_CLAK_LOG_COLORS_RAW) if _CLAK_LOG_COLORS_RAW is not None else None
)

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


# Enable debug logging if CLAK_DEBUG environment variable is set to 1
if CLAK_DEBUG:
    import logging

    register_clak_log_levels()

    if CLAK_COLORS:
        try:
            import coloredlogs

            apply_coloredlogs_defaults(coloredlogs)
            coloredlogs.install(level="DEBUG")
        except ImportError:
            pass
    else:
        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(levelname)8s] %(name)s - %(message)s",
        )

    logger = logging.getLogger()
    logger.debug(
        "Debug logging enabled via CLAK_DEBUG=%s with CLAK_COLORS=%s",
        CLAK_DEBUG,
        CLAK_COLORS,
    )
