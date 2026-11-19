"""Prompt policy: decide whether components may read input, and who answers.

A :class:`UIPolicy` is shared by components (``policy=`` kwarg) or bound once
in a :class:`UISession`. It holds two things:

- ``interactive``: may components read answers from the user?
- ``responders``: ordered, non-blocking answerers tried *before* reading
  (``--yes``, defaults, preseeded answers...). Any callable taking a
  :class:`Question` and returning an answer or ``NO_ANSWER`` is a responder.

If no responder answers and the policy is not interactive, the component
raises :class:`UINoInputError` instead of blocking.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import IO, Any, Callable, Mapping, Optional, Sequence

from .base import UIAbort


class _NoAnswer:
    """Sentinel type: a responder had no answer."""

    def __repr__(self) -> str:
        return "NO_ANSWER"

    def __bool__(self) -> bool:
        return False


NO_ANSWER = _NoAnswer()

FALSE_ENV_VALUES = frozenset({"", "0", "false", "no", "off"})


class UINoInputError(UIAbort):
    """Input was required but the policy forbids prompting."""


@dataclass(frozen=True)
class Question:
    """What a component is about to ask."""

    kind: str  # "text" | "confirm" | "choice"
    message: str
    default: Any = None
    choices: Optional[Sequence[Any]] = None
    required: bool = True
    dangerous: bool = False


Responder = Callable[[Question], Any]


class YesResponder:
    """Answer every confirmation with yes (including dangerous ones)."""

    def __call__(self, question: Question) -> Any:
        return True if question.kind == "confirm" else NO_ANSWER


class DefaultsResponder:
    """Answer with the question default; refuse dangerous confirmations.

    A non-required question without default is answered ``None``.
    """

    def __call__(self, question: Question) -> Any:
        if question.dangerous:
            return NO_ANSWER
        if question.default is not None:
            return question.default
        if not question.required:
            return None
        return NO_ANSWER


class MappingResponder:
    """Preseeded answers keyed by question message (tests, answer files)."""

    def __init__(self, answers: Mapping[str, Any]):
        self.answers = dict(answers)

    def __call__(self, question: Question) -> Any:
        return self.answers.get(question.message, NO_ANSWER)


def detect_interactive(
    stdin: Optional[IO[str]] = None,
    stderr: Optional[IO[str]] = None,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    """Autodetect: True only for a TTY on stdin **and** stderr, outside CI.

    ``CI`` set to anything but ``0/false/no/off`` forces False.
    """
    import sys  # pylint: disable=import-outside-toplevel

    env = os.environ if env is None else env
    if str(env.get("CI", "")).strip().lower() not in FALSE_ENV_VALUES:
        return False
    stdin = stdin or sys.stdin
    stderr = stderr or sys.stderr
    try:
        return bool(stdin.isatty() and stderr.isatty())
    except (AttributeError, ValueError):
        return False


@dataclass(frozen=True)
class UIPolicy:
    """Interactivity switch plus ordered responders."""

    interactive: bool = True
    responders: tuple = ()
    hint: str = ""  # appended to "input required" errors
    yes_hint: str = ""  # appended to dangerous-confirm errors

    @classmethod
    def build(
        cls,
        interactive: bool,
        assume_yes: bool = False,
        **kwargs,
    ) -> "UIPolicy":
        """Standard policy: ``[Yes?]`` then ``[Defaults]`` when not interactive."""
        responders: list = []
        if assume_yes:
            responders.append(YesResponder())
        if not interactive:
            responders.append(DefaultsResponder())
        return cls(interactive=interactive, responders=tuple(responders), **kwargs)

    @classmethod
    def auto(cls, assume_yes: bool = False, **detect) -> "UIPolicy":
        """Policy from TTY / ``CI`` detection (see :func:`detect_interactive`)."""
        return cls.build(detect_interactive(**detect), assume_yes)

    @classmethod
    def always(cls, assume_yes: bool = False) -> "UIPolicy":
        """Always prompt."""
        return cls.build(True, assume_yes)

    @classmethod
    def never(cls, assume_yes: bool = False) -> "UIPolicy":
        """Never prompt: defaults or fail."""
        return cls.build(False, assume_yes)

    def answer(self, question: Question) -> Any:
        """Return an answer, ``NO_ANSWER`` (go read input), or raise.

        Raises:
            UINoInputError: nobody answered and prompting is forbidden.
        """
        for responder in self.responders:
            value = responder(question)
            if value is not NO_ANSWER:
                return value
        if self.interactive:
            return NO_ANSWER
        if question.dangerous:
            msg = f"confirmation required: {question.message}"
            hint = self.yes_hint
        else:
            msg = f"input required: {question.message}"
            hint = self.hint
        raise UINoInputError(f"{msg} ({hint})" if hint else msg)
