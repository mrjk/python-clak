"""Process / env context: settings, runtime snapshot, facts, log levels.

Import helpers from the submodules; ``clak.runtime.facts`` is loaded only
when ``ctx.facts`` is first used.
"""

from clak.runtime.runtime import (
    COLOR_16,
    COLOR_256,
    COLOR_NONE,
    COLOR_TRUECOLOR,
    RuntimeInfo,
    detect_runtime,
)
from clak.runtime.settings import ClakSettings

__all__ = [
    "COLOR_16",
    "COLOR_256",
    "COLOR_NONE",
    "COLOR_TRUECOLOR",
    "ClakSettings",
    "RuntimeInfo",
    "detect_runtime",
]
