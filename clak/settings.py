"Common clak settings"

import os
import sys

from clak.common import to_boolean
from clak.log_levels import CLAK_CUSTOM_LEVEL_STYLES, register_clak_log_levels

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


def resolve_log_colors(cli_value=None, stream=None):
    """Resolve whether colored logs should be enabled.

    Precedence:
    1. Explicit CLI ``--log-colors`` / ``--no-log-colors`` (``cli_value`` not None)
    2. ``CLAK_LOG_COLORS`` when set
    3. Auto: ``CLAK_COLORS`` and ``stream.isatty()`` (default stream: stderr)
    """
    if cli_value is not None:
        return bool(cli_value)
    if CLAK_LOG_COLORS is not None:
        return bool(CLAK_LOG_COLORS)
    if stream is None:
        stream = sys.stderr
    return bool(CLAK_COLORS) and stream.isatty()


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
