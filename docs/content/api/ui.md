# UI

Interactive components (prompts, confirmations, continue/quit, wait spinner).
Standard library only and portable: copy `clak/ui/` into any project.

See the [UI guide](../docs/ui.md) for usage.

::: clak.ui
    options:
      show_source: false
      members:
        - UIComponent
        - UIAbort
        - TextPrompt
        - ConfirmPrompt
        - ChoicePrompt
        - ContinuePrompt
        - WaitSpinner
