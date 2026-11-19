"""Shared base for interactive UI components (stdlib only)."""

from __future__ import annotations

import sys
from typing import IO, Optional


class UIAbort(Exception):
    """Raised when the user aborts an interaction (Ctrl-C / Ctrl-D / quit)."""


class UIComponent:
    """Base class: holds input/output streams so components are testable.

    Prompts and messages go to ``stderr`` by default so ``stdout`` stays
    clean for piped data.
    """

    def __init__(
        self,
        *,
        stdin: Optional[IO[str]] = None,
        stderr: Optional[IO[str]] = None,
        interactive: Optional[bool] = None,
    ):
        self.stdin = stdin
        self.stderr = stderr
        self._interactive = interactive

    @property
    def _in(self) -> IO[str]:
        return self.stdin or sys.stdin

    @property
    def _out(self) -> IO[str]:
        return self.stderr or sys.stderr

    @property
    def interactive(self) -> bool:
        """True when both input and output are terminals."""
        if self._interactive is not None:
            return self._interactive
        try:
            return self._in.isatty() and self._out.isatty()
        except (AttributeError, ValueError):
            return False

    def write(self, text: str = "", end: str = "\n") -> None:
        """Write text to the UI stream."""
        self._out.write(text + end)
        self._out.flush()

    def readline(self, prompt: str = "") -> str:
        """Read one line (without newline). Raises UIAbort on EOF/Ctrl-C."""
        self._out.write(prompt)
        self._out.flush()
        try:
            line = self._in.readline()
        except KeyboardInterrupt as err:
            self.write()
            raise UIAbort("interrupted") from err
        if line == "":
            self.write()
            raise UIAbort("end of input")
        return line.rstrip("\r\n")
