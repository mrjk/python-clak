"""Interactive UI components (prompts, confirmations, pauses, waits).

Standard library only, self-contained and portable: relative imports only and
no clak dependency, so this folder can be copied as-is into any project.
Prompts go to stderr by default so stdout stays clean for piped data.
"""

from .base import UIComponent, UIAbort
from .flow import ContinuePrompt, WaitSpinner, prompt_continue, wait_spinner
from .policy import (
    NO_ANSWER,
    DefaultsResponder,
    MappingResponder,
    Question,
    UINoInputError,
    UIPolicy,
    YesResponder,
    detect_interactive,
)
from .prompt import (
    ChoicePrompt,
    ConfirmPrompt,
    TextPrompt,
    prompt_choice,
    prompt_confirm,
    prompt_text,
)
from .session import UISession

__all__ = [
    "NO_ANSWER",
    "DefaultsResponder",
    "MappingResponder",
    "Question",
    "UINoInputError",
    "UIPolicy",
    "UISession",
    "YesResponder",
    "detect_interactive",
    "ChoicePrompt",
    "UIComponent",
    "ConfirmPrompt",
    "ContinuePrompt",
    "TextPrompt",
    "UIAbort",
    "WaitSpinner",
    "prompt_choice",
    "prompt_confirm",
    "prompt_continue",
    "prompt_text",
    "wait_spinner",
]
