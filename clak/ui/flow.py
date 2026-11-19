"""Flow control components: ContinuePrompt (continue/quit) and WaitSpinner."""

from __future__ import annotations

import itertools
import threading
import time
from typing import Optional

from .base import UIComponent, UIAbort

QUIT_WORDS = frozenset({"q", "quit", "n", "no", "exit"})


class ContinuePrompt(UIComponent):
    """Pause until the user presses Enter; ``q`` quits (raises UIAbort).

    Non-interactive sessions never block: ``ask()`` returns True immediately.
    """

    def __init__(
        self,
        message: str = "Press Enter to continue, q to quit",
        *,
        raise_on_quit: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.message = message
        self.raise_on_quit = raise_on_quit

    def ask(self) -> bool:
        """Return True to continue, False to quit (or raise UIAbort)."""
        if not self.interactive:
            return True
        try:
            raw = self.readline(f"{self.message} ").strip().lower()
        except UIAbort:
            if self.raise_on_quit:
                raise
            return False
        if raw in QUIT_WORDS:
            if self.raise_on_quit:
                raise UIAbort("quit")
            return False
        return True


class WaitSpinner(UIComponent):
    """Show a message (with a spinner on TTY) while work runs.

    Use as a context manager, or call ``sleep(seconds)``::

        with WaitSpinner("Loading"):
            do_work()
    """

    FRAMES = "|/-\\"

    def __init__(self, message: str = "Please wait", *, interval: float = 0.1, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.interval = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _spin(self) -> None:
        for frame in itertools.cycle(self.FRAMES):
            if self._stop.is_set():
                break
            self._out.write(f"\r{frame} {self.message}")
            self._out.flush()
            time.sleep(self.interval)

    def start(self) -> None:
        """Start displaying the wait indicator."""
        if not self.interactive:
            self.write(f"{self.message}...")
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, done: str = "done") -> None:
        """Stop the indicator and print the final status."""
        if self._thread is not None:
            self._stop.set()
            self._thread.join()
            self._thread = None
            self._out.write("\r" + " " * (len(self.message) + 2) + "\r")
            self.write(f"{self.message}... {done}")
        elif not self.interactive:
            self.write(f"{self.message}... {done}")

    def sleep(self, seconds: float) -> None:
        """Wait for ``seconds`` with the indicator displayed."""
        with self:
            time.sleep(seconds)

    def __enter__(self) -> "WaitSpinner":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop("failed" if exc_type else "done")


def prompt_continue(message: str = "Press Enter to continue, q to quit", **kwargs) -> bool:
    """Shortcut for ``ContinuePrompt(message, **kwargs).ask()``."""
    return ContinuePrompt(message, **kwargs).ask()


def wait_spinner(message: str = "Please wait", **kwargs) -> WaitSpinner:
    """Shortcut returning a ``WaitSpinner`` context manager."""
    return WaitSpinner(message, **kwargs)


__all__ = ["ContinuePrompt", "WaitSpinner", "prompt_continue", "wait_spinner"]
