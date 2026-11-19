"""Question components: TextPrompt, ConfirmPrompt, ChoicePrompt."""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from .base import UIAbort, UIComponent
from .policy import NO_ANSWER

TRUE_WORDS = frozenset({"y", "yes", "true", "1", "on"})
FALSE_WORDS = frozenset({"n", "no", "false", "0", "off"})


class TextPrompt(UIComponent):
    """Ask for a free text value, with default, cast and validation."""

    def __init__(
        self,
        message: str,
        *,
        default: Any = None,
        cast: Optional[Callable[[str], Any]] = None,
        validate: Optional[Callable[[Any], Any]] = None,
        required: bool = True,
        max_tries: int = 3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.message = message
        self.default = default
        self.cast = cast
        self.validate = validate
        self.required = required
        self.max_tries = max_tries

    def ask(self) -> Any:
        """Return the answer. Raises UIAbort on abort or too many bad answers."""
        pre = self.preanswer(
            "text", self.message, default=self.default, required=self.required
        )
        if pre is not NO_ANSWER:
            return pre
        suffix = f" [{self.default}]" if self.default is not None else ""
        for _ in range(self.max_tries):
            raw = self.readline(f"{self.message}{suffix}: ").strip()
            if not raw:
                if self.default is not None:
                    return self.default
                if self.required:
                    self.write("A value is required.")
                    continue
                return None
            try:
                value = self.cast(raw) if self.cast else raw
                if self.validate is not None:
                    # validate may return False or raise ValueError
                    if self.validate(value) is False:
                        raise ValueError("invalid value")
            except ValueError as err:
                self.write(f"Invalid: {err}")
                continue
            return value
        raise UIAbort("too many invalid answers")


class ConfirmPrompt(UIComponent):
    """Yes / no question."""

    def __init__(
        self,
        message: str,
        *,
        default: Optional[bool] = None,
        dangerous: bool = False,
        **kwargs,
    ):
        """``dangerous``: never accepted from defaults, only an explicit yes."""
        super().__init__(**kwargs)
        self.message = message
        self.default = default
        self.dangerous = dangerous

    def ask(self) -> bool:
        """Return True/False. Raises UIAbort on abort."""
        pre = self.preanswer(
            "confirm", self.message, default=self.default, dangerous=self.dangerous
        )
        if pre is not NO_ANSWER:
            return pre
        hint = {True: "[Y/n]", False: "[y/N]", None: "[y/n]"}[self.default]
        while True:
            raw = self.readline(f"{self.message} {hint} ").strip().lower()
            if not raw and self.default is not None:
                return self.default
            if raw in TRUE_WORDS:
                return True
            if raw in FALSE_WORDS:
                return False
            self.write("Please answer yes or no.")


class ChoicePrompt(UIComponent):
    """Pick one item from a numbered list (number or exact label)."""

    def __init__(
        self,
        message: str,
        choices: Sequence[Any],
        *,
        default: Optional[Any] = None,
        max_tries: int = 3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if not choices:
            raise ValueError("choices must not be empty")
        self.message = message
        self.choices = list(choices)
        self.default = default
        self.max_tries = max_tries

    def ask(self) -> Any:
        """Return the selected item. Raises UIAbort on abort / bad answers."""
        pre = self.preanswer(
            "choice", self.message, default=self.default, choices=self.choices
        )
        if pre is not NO_ANSWER:
            return pre
        self.write(self.message)
        for idx, item in enumerate(self.choices, 1):
            self.write(f"  {idx}) {item}")
        suffix = f" [{self.default}]" if self.default is not None else ""
        for _ in range(self.max_tries):
            raw = self.readline(f"Choice{suffix}: ").strip()
            if not raw and self.default is not None:
                return self.default
            if raw.isdigit() and 1 <= int(raw) <= len(self.choices):
                return self.choices[int(raw) - 1]
            for item in self.choices:
                if str(item) == raw:
                    return item
            self.write(f"Enter a number between 1 and {len(self.choices)}.")
        raise UIAbort("too many invalid answers")


def prompt_text(message: str, **kwargs) -> Any:
    """Shortcut for ``TextPrompt(message, **kwargs).ask()``."""
    return TextPrompt(message, **kwargs).ask()


def prompt_confirm(message: str, **kwargs) -> bool:
    """Shortcut for ``ConfirmPrompt(message, **kwargs).ask()``."""
    return ConfirmPrompt(message, **kwargs).ask()


def prompt_choice(message: str, choices: Sequence[Any], **kwargs) -> Any:
    """Shortcut for ``ChoicePrompt(message, choices, **kwargs).ask()``."""
    return ChoicePrompt(message, choices, **kwargs).ask()
