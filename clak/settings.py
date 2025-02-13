"Common clak settings"

import os

from clak.common import to_boolean

CLAK_DEBUG = to_boolean(os.environ.get("CLAK_DEBUG", False))
CLAK_COLORS = to_boolean(os.environ.get("CLAK_COLORS", True))

# if LOG_STYLES:
LOG_STYLES = {
    "spam": {"color": "grey", "faint": True},
    "debug": {"color": "magenta"},
    "verbose": {"color": "cyan"},
    "info": {"color": "blue"},
    "notice": {"color": "green"},
    "warning": {"color": "yellow"},
    "success": {"color": "green", "bold": True},
    "error": {"color": "red"},
    "critical": {"color": "red", "bold": True},
}
LOG_FORMAT = "[%(levelname)8s] %(message)s"

# Enable debug logging if CLAK_DEBUG environment variable is set to 1
if CLAK_DEBUG:

    # Import required libraries
    if CLAK_COLORS:
        try:
            import logging

            import coloredlogs

            coloredlogs.DEFAULT_LEVEL_STYLES = LOG_STYLES
            coloredlogs.DEFAULT_LOG_FORMAT = LOG_FORMAT
            coloredlogs.install(level="DEBUG")
        except ImportError:
            pass
    else:
        import logging

        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(levelname)8s] %(name)s - %(message)s",
        )

    # Configure logging
    logger = logging.getLogger()
    logger.debug(
        "Debug logging enabled via CLAK_DEBUG=%s with CLAK_COLORS=%s",
        CLAK_DEBUG,
        CLAK_COLORS,
    )
