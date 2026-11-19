"""UISession: bind one policy (and streams) once, build components from it."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from .base import UIComponent
from .flow import ContinuePrompt, WaitSpinner
from .policy import UIPolicy
from .prompt import ChoicePrompt, ConfirmPrompt, TextPrompt


class UISession:
    """Factory shortcuts sharing a policy and component kwargs (streams...)."""

    def __init__(self, policy: Optional[UIPolicy] = None, **component_kwargs):
        self.policy = policy or UIPolicy.auto()
        self.component_kwargs = component_kwargs

    def _make(self, cls, *args, **kwargs):
        opts = {**self.component_kwargs, "policy": self.policy, **kwargs}
        return cls(*args, **opts)

    def _run(self, component: UIComponent) -> Any:
        """Run ``component.ask()``. Subclasses may translate exceptions."""
        return component.ask()

    def text(self, message: str, **kwargs) -> Any:
        """Ask for text (see ``TextPrompt``)."""
        return self._run(self._make(TextPrompt, message, **kwargs))

    def confirm(self, message: str, **kwargs) -> bool:
        """Ask yes/no (see ``ConfirmPrompt``)."""
        return self._run(self._make(ConfirmPrompt, message, **kwargs))

    def choice(self, message: str, choices: Sequence[Any], **kwargs) -> Any:
        """Ask for one item (see ``ChoicePrompt``)."""
        return self._run(self._make(ChoicePrompt, message, choices, **kwargs))

    def pause(self, message: Optional[str] = None, **kwargs) -> bool:
        """Continue / quit pause (see ``ContinuePrompt``)."""
        args = (message,) if message else ()
        return self._run(self._make(ContinuePrompt, *args, **kwargs))

    def spinner(self, message: str = "Please wait", **kwargs) -> WaitSpinner:
        """Wait spinner context manager (see ``WaitSpinner``)."""
        return self._make(WaitSpinner, message, **kwargs)
