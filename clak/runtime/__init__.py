"""Process / env context: runtime snapshot, facts, settings, log levels."""

from clak.runtime.facts import FactsInfo, IdentityInfo, detect_facts
from clak.runtime.log_levels import (
    CLAK_CUSTOM_LEVEL_STYLES,
    CLAK_CUSTOM_LEVELS,
    add_logging_level,
    register_clak_log_levels,
)
from clak.runtime.runtime import (
    COLOR_16,
    COLOR_256,
    COLOR_NONE,
    COLOR_TRUECOLOR,
    DEFAULT_NARROW_WIDTH,
    DEFAULT_TERM_HEIGHT,
    DEFAULT_TERM_WIDTH,
    RuntimeInfo,
    detect_runtime,
)
from clak.runtime.settings import (
    CLAK_COLORS,
    CLAK_DEBUG,
    CLAK_LOG_COLORS,
    LOG_FORMAT,
    LOG_STYLES,
    apply_coloredlogs_defaults,
    resolve_log_colors,
)

__all__ = [
    "CLAK_COLORS",
    "CLAK_CUSTOM_LEVEL_STYLES",
    "CLAK_CUSTOM_LEVELS",
    "CLAK_DEBUG",
    "CLAK_LOG_COLORS",
    "COLOR_16",
    "COLOR_256",
    "COLOR_NONE",
    "COLOR_TRUECOLOR",
    "DEFAULT_NARROW_WIDTH",
    "DEFAULT_TERM_HEIGHT",
    "DEFAULT_TERM_WIDTH",
    "FactsInfo",
    "IdentityInfo",
    "LOG_FORMAT",
    "LOG_STYLES",
    "RuntimeInfo",
    "add_logging_level",
    "apply_coloredlogs_defaults",
    "detect_facts",
    "detect_runtime",
    "register_clak_log_levels",
    "resolve_log_colors",
]
