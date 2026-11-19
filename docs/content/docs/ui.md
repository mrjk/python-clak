# Interactive UI

`clak.ui` provides small interactive components: text prompts, yes/no
confirmations, choice menus, continue/quit pauses and a wait spinner.

- **Standard library only.**
- **Portable.** The package uses relative imports and does not depend on the
  rest of clak. Copy it into any project: `cp -r clak/ui myproj/ui`.
- **Pipe friendly.** Prompts are written to `stderr`, so `stdout` stays clean.
- **Testable.** Every component accepts `stdin=` and `stderr=` streams.

Output rendering (tables, JSON, ...) is a separate topic, see [Views](views.md).

## Components

| Class | Shortcut | Purpose |
|---|---|---|
| `TextPrompt` | `prompt_text()` | Free text, with default, `cast`, `validate`, `required` |
| `ConfirmPrompt` | `prompt_confirm()` | Yes / no, optional default |
| `ChoicePrompt` | `prompt_choice()` | Numbered menu; answer by number or exact label |
| `ContinuePrompt` | `prompt_continue()` | Press Enter to continue, `q` to quit |
| `WaitSpinner` | `wait_spinner()` | Spinner context manager while work runs |

All inherit from `UIComponent`. Shortcuts take the same arguments as the class
constructor and (for prompts) return the answer directly.

```python
from clak.ui import (
    ChoicePrompt, ConfirmPrompt, ContinuePrompt, TextPrompt, WaitSpinner, UIAbort,
)

name = TextPrompt("Name", default="anonymous").ask()
age = TextPrompt("Age", cast=int, validate=lambda v: v > 0).ask()
role = ChoicePrompt("Role", ["admin", "dev", "guest"], default="dev").ask()

if ConfirmPrompt("Proceed?", default=True).ask():
    with WaitSpinner("Working"):
        do_work()
```

## Validation and retries

`TextPrompt` and `ChoicePrompt` retry up to `max_tries` times (default 3), then
raise `UIAbort`. `cast` may raise `ValueError`; `validate` may raise
`ValueError` or return `False`. Both print a message and re-ask.

## Aborting

Ctrl-C, end of input and too many invalid answers raise `UIAbort`.
`ContinuePrompt` returns `False` on quit instead, unless `raise_on_quit=True`.

```python
try:
    ...
except UIAbort:
    sys.exit(130)
```

## Non-interactive sessions

Without a policy, components keep it simple: `ContinuePrompt` returns `True`
when the session is not a terminal, `WaitSpinner` prints plain lines, and other
prompts read lines from stdin (so piped answers work). Force the detection with
`interactive=True|False`.

For real automation use a policy, below.

## Policies and responders

A `UIPolicy` says whether prompting is allowed and who may answer without
asking. Pass it to a component (`policy=`) or bind it once in a `UISession`.

```python
from clak.ui import UIPolicy, UISession

ui = UISession(UIPolicy.never(assume_yes=True))   # CI: defaults, yes to confirms
ui = UISession(UIPolicy.auto())                    # TTY and not CI: prompt
ui.confirm("Deploy?", default=True)
ui.text("Name")                                    # raises UINoInputError, no default
```

| Policy | Behaviour |
| --- | --- |
| `UIPolicy.always()` | Prompt (optionally answering confirms with `assume_yes`) |
| `UIPolicy.never()` | Never read input: defaults, else `UINoInputError` |
| `UIPolicy.auto()` | `always` on a TTY outside CI (`detect_interactive`), else `never` |

Responders are tried in order before any input is read. A responder is any
callable taking a `Question` and returning an answer or `NO_ANSWER`:

| Responder | Answers |
| --- | --- |
| `YesResponder` | every confirmation, dangerous ones included |
| `DefaultsResponder` | the default; refuses `dangerous` confirms |
| `MappingResponder(dict)` | preseeded answers by message (tests, answer files) |

```python
UIPolicy(interactive=False, responders=(MappingResponder({"Name": "ada"}), DefaultsResponder()))
```

`ConfirmPrompt(..., dangerous=True)` is never accepted from a default. The CLI
side (`--no-input`, `--yes`, `CI`) is handled by
[`RuntimeOptMixin`](unattended.md).

## Testing

```python
import io
from clak.ui import ConfirmPrompt

out = io.StringIO()
assert ConfirmPrompt("ok?", stdin=io.StringIO("y\n"), stderr=out).ask() is True
```

## Example

See `examples/script_ui.py` (run with `--no-input`, `--yes`, `--interactive=always`).

## Extending

Subclass `UIComponent` and use `self.write()` / `self.readline()`; they handle
streams and raise `UIAbort` on EOF and Ctrl-C.
