"""Named argparse behavior flags for Python 3.10-3.14."""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ArgparseCapabilities:
    """What this interpreter's argparse actually does.

    Branch on these flags instead of catching TypeError or sniffing messages.
    """

    has_color_kwarg: bool
    error_always_raises: bool
    intermixed_reenters: bool
    intermixed_slices_usage: bool
    choice_quotes_in_errors: bool

    @classmethod
    def detect(cls, version=None) -> "ArgparseCapabilities":
        """Build flags from ``sys.version_info`` (or an explicit pair)."""
        ver = version if version is not None else sys.version_info[:2]
        return cls(
            has_color_kwarg=ver >= (3, 14),
            error_always_raises=ver >= (3, 12),
            intermixed_reenters=ver < (3, 12),
            intermixed_slices_usage=ver < (3, 12),
            choice_quotes_in_errors=ver != (3, 12),
        )
