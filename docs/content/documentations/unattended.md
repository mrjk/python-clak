# Attended vs unattended runs (`RuntimeOptMixin`)

Prompts block. In scripts, cron or CI that means hangs, or prompts that
swallow piped data. `RuntimeOptMixin` adds familiar flags so the same command
works at a terminal and in automation.

```python
from clak import Parser, RuntimeOptMixin
from clak.comp.runtime import ui_session


class App(RuntimeOptMixin, Parser):
    def cli_run(self, ctx, **_):
        ui = ui_session(ctx)
        name = ui.text("Name", default="anonymous")
        if ui.confirm("Create it?", default=True):
            ...
```

## Flags

| Flag | Prior art | Meaning |
| --- | --- | --- |
| `--interactive WHEN` | `ls --color=WHEN` | `auto` (default), `always` or `never` |
| `--no-input` | pip, gcloud, Django | Same as `--interactive=never` |
| `-y`, `--yes` | apt, dnf, gh | Answer confirmations with yes |

- `--yes` only affects confirmations. `--yes --no-input` is the usual CI
  combination. `--yes` alone on a terminal still asks other questions.
- `--no-input` together with `--interactive always|auto` is an error.
- There are no short flags: `-n` usually means dry-run and `-i` ask-each.

## How the mode is chosen

First match wins:

1. CLI: `--no-input` or `--interactive WHEN`
2. Environment: `CLAK_INTERACTIVE=auto|always|never` (also `1/0/true/false`)
3. `CI` set to anything but empty, `0`, `false`, `no`, `off` means never
4. Terminal on **both** stdin and stderr means interactive, else never

`--interactive=auto` explicitly resets an environment override. There is no
environment variable for `--yes`, so a stray export cannot auto-confirm
deletions.

## What unattended means for prompts

| Prompt | Unattended behaviour |
| --- | --- |
| Text, choice | The default; no default means an error (a non-`required` text gives `None`) |
| Confirm | The default; `--yes` gives yes; no default means an error |
| Dangerous confirm | **Only** `--yes` accepts it. Defaults are ignored, so `--no-input` alone fails safe |
| Continue | Continues immediately |
| Spinner | Plain `message...` / `message... done` lines |

Errors are clean one-liners with exit code 1 (no traceback):

```text
$ app --no-input
input required: Name (use --interactive=always to allow prompting)
$ app --no-input --delete
confirmation required: Delete all previous users? (pass --yes to confirm)
```

Mark destructive questions explicitly:

```python
ui.confirm("Delete all previous users?", dangerous=True)
```

## Edge cases

- **stdin carries data** (`cat file | app`): stdin is not a TTY, so `auto`
  does not read answers from it. Force it with `--interactive=always`.
- **stdout piped** (`app | jq`): still interactive; prompts go to stderr.
- **stderr redirected** (`2>log`): the prompt would be invisible, so `auto`
  turns prompting off.
- **Subcommands:** put the mixin on the root parser; values are published once.
- **Secrets** and prompt **timeouts** are not handled yet.

## Using the values without clak.ui

The mixin publishes plain values on the context, usable by any mixin or command:

```python
ctx.interactive   # bool
ctx.assume_yes    # bool
ctx.plugins["runtime"]  # {"interactive", "assume_yes", "mode", "source"}
```

`resolve_runtime(args, env, stdin, stderr)` is a pure function for tests.

## Custom behaviour

`clak.ui` answers unattended questions through *responders*, see the
[UI guide](ui.md#policies-and-responders). `ui_policy(ctx)` builds the standard
policy; build your own `UIPolicy` for other needs.

## Custom flags

`ui_session(ctx)` is not tied to `RuntimeOptMixin`: it only reads the generic UI
settings in `ctx.plugins["ui_settings"]` (also `ctx.ui_settings`). Producers fill
them with `set_ui_settings()`, consumers just call `ui_session(ctx)`.

| Key | Meaning |
| --- | --- |
| `interactive` | may prompt (missing: TTY / `CI` autodetection) |
| `assume_yes` | answer confirmations with yes |
| `hint` / `yes_hint` | appended to "input required" / "confirmation required" errors |
| `responders` | extra responders tried first (appended across calls) |
| anything else | passed to components (`stdin`, `stderr`...) |

`RuntimeOptMixin` is just one producer. With your own flags:

```python
from clak import Parser
from clak.comp.runtime import set_ui_settings, ui_session
from clak.core.descriptors import Argument


class App(Parser):
    batch = Argument("--batch", action="store_true", help="Never prompt")
    force = Argument("--force", action="store_true", help="Assume yes")

    def cli_hook__ui(self, instance, ctx, **_):
        set_ui_settings(
            ctx,
            interactive=not ctx.args.batch,
            assume_yes=ctx.args.force,
            hint="drop --batch to allow prompting",
            yes_hint="pass --force",
        )

    def cli_run(self, ctx, **_):
        if ui_session(ctx).confirm("Delete everything?", dangerous=True):
            ...
```

For a one-off, pass a policy directly: `ui_session(ctx, policy=UIPolicy.never())`,
or override settings: `ui_policy(ctx, interactive=True)`.
