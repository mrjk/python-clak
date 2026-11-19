"""Interactive UI components (prompts, confirmations, pauses, waits).

Standard library only, self-contained and portable: relative imports only and
no clak dependency, so this folder can be copied as-is into any project.
Prompts go to stderr by default so stdout stays clean for piped data.
"""

from .base import UIComponent, UIAbort
from .flow import ContinuePrompt, WaitSpinner, prompt_continue, wait_spinner
from .prompt import (
    ChoicePrompt,
    ConfirmPrompt,
    TextPrompt,
    prompt_choice,
    prompt_confirm,
    prompt_text,
)

__all__ = [
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
