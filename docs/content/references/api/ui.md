# UI

Interactive components (prompts, confirmations, continue/quit, wait spinner).
Standard library only and portable: copy `clak/ui/` into any project.

See the [UI guide](../../documentations/ui.md) for usage.

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
        - UIPolicy
        - UISession
        - Question
        - UINoInputError
        - YesResponder
        - DefaultsResponder
        - MappingResponder
        - detect_interactive

## Runtime flags

See the [unattended runs guide](../../documentations/unattended.md).

::: clak.comp.runtime
    options:
      show_source: false
      members:
        - RuntimeOptMixin
        - resolve_runtime
        - set_ui_settings
        - ui_policy
        - ui_session
