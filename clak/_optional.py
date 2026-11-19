"""Optional third-party dependencies: probe, import, and install hints.

Single place that knows which ``mrjk.clak[extra]`` ships which package.
Imports go through ``__import__`` so tests can simulate a missing package
by patching ``builtins.__import__``.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Optional

from clak.exception import ClakUserError

# Top-level package -> (pip distribution name, clak extra)
_EXTRAS = {
    "yaml": ("PyYAML", "config"),
    "rich": ("rich", "markdown"),
    "docutils": ("docutils", "rst"),
    "coloredlogs": ("coloredlogs", "colors"),
}


def install_hint(module: str) -> str:
    """``pip install`` command for the extra that provides *module*."""
    _dist, extra = _EXTRAS[module.split(".", 1)[0]]
    return f"pip install 'mrjk.clak[{extra}]'"


def optional(module: str) -> Optional[ModuleType]:
    """Import *module* (dotted names allowed) or return None if missing."""
    try:
        __import__(module)
    except ImportError:
        return None
    return sys.modules[module]


def available(module: str) -> bool:
    """Whether *module* can be imported."""
    return optional(module) is not None


def require(module: str, purpose: str) -> ModuleType:
    """Import *module* or raise ``ClakUserError`` with the install hint.

    *purpose* completes "<purpose> requires the <dist> package", e.g.
    ``require("yaml", "YAML output")``.
    """
    try:
        __import__(module)
    except ImportError as err:
        dist, _extra = _EXTRAS[module.split(".", 1)[0]]
        raise ClakUserError(
            f"{purpose} requires the {dist} package",
            advice=f"Install with: {install_hint(module)}",
        ) from err
    return sys.modules[module]
