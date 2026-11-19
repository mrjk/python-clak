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

When stdin/stderr are not terminals (`UIComponent.interactive` is false):

- `ContinuePrompt` returns `True` immediately, never blocking.
- `WaitSpinner` prints plain `message...` / `message... done` lines, with no
  animation.
- Other prompts still read lines from stdin, so piped answers work.

Force the detection with `interactive=True|False`.

## Testing

```python
import io
from clak.ui import ConfirmPrompt

out = io.StringIO()
assert ConfirmPrompt("ok?", stdin=io.StringIO("y\n"), stderr=out).ask() is True
```

## Example

See `examples/script_ui.py`.

## Extending

Subclass `UIComponent` and use `self.write()` / `self.readline()`; they handle
streams and raise `UIAbort` on EOF and Ctrl-C.
