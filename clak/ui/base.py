"""Shared base for interactive UI components (stdlib only)."""

from __future__ import annotations

import sys
from typing import IO, TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .policy import UIPolicy


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
        policy: Optional["UIPolicy"] = None,
    ):
        self.stdin = stdin
        self.stderr = stderr
        self.policy = policy
        self._interactive = interactive

    @property
    def _in(self) -> IO[str]:
        return self.stdin or sys.stdin

    @property
    def _out(self) -> IO[str]:
        return self.stderr or sys.stderr

    @property
    def interactive(self) -> bool:
        """True when prompting is allowed (see ``policy.detect_interactive``).

        Explicit ``interactive`` wins, then the policy, then autodetection
        on this component's streams (TTY on input and output, outside CI).
        """
        if self._interactive is not None:
            return self._interactive
        if self.policy is not None:
            return self.policy.interactive
        # Local import: policy imports this module.
        from .policy import (  # pylint: disable=import-outside-toplevel
            detect_interactive,
        )

        return detect_interactive(self._in, self._out)

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

    def preanswer(self, kind: str, message: str, **fields: Any) -> Any:
        """Ask the policy first. Returns an answer or ``NO_ANSWER``.

        Without a policy nothing is decided here: the component reads input.
        Raises ``UINoInputError`` when prompting is forbidden and nobody answers.
        """
        # pylint: disable=import-outside-toplevel
        from .policy import NO_ANSWER, Question

        if self.policy is None:
            return NO_ANSWER
        return self.policy.answer(Question(kind, message, **fields))
