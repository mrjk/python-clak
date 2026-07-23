# Shell completion

Clak can **emit** shell completion scripts via [argcomplete](https://kislyuk.github.io/argcomplete/).
`argcomplete` is a core dependency of `mrjk.clak`.

API reference: [Completion component](../api/plugin_complete.md).

Runtime tab-completion during `parse_args` (calling `argcomplete.autocomplete()`)
is still on the [roadmap](../project/roadmap.md). What ships today is **script
generation** so users can register your CLI with their shell.

## Recommended pattern: `completion` subcommand

Attach `CompCmdRender` as a subcommand:

```python
from clak import CompCmdRender, Command, Parser

class App(Parser):
    """My application."""

    completion = Command(
        CompCmdRender,
        help="Print shell completion script for this app",
    )

    def cli_run(self, **_):
        print("Run a subcommand, or: eval \"$(myapp completion)\"")

if __name__ == "__main__":
    App()
```

Generate and enable (bash):

```bash
# Preview
python myapp.py completion --shell bash

# Enable for the current shell session (use your real executable name)
eval "$(python myapp.py completion --executable myapp --shell bash)"
```

Useful flags on the `completion` command:

| Flag | Default | Purpose |
| --- | --- | --- |
| `-s` / `--shell` | `bash` | `bash`, `zsh`, `tcsh`, `fish`, `powershell` |
| `--executable` | (see mixin) | Name(s) of the executable to complete |
| `--no-defaults` | off | Bash only: do not fall back to readline defaults |
| `--complete-arguments` | — | Bash only: custom `complete` arguments |

Fish example (write a snippet, then source it):

```bash
python myapp.py completion --shell fish --executable myapp \
  > ~/.config/fish/completions/myapp.fish
```

## Alternative: `--completion` flag

`CompRenderOptMixin` adds a top-level `--completion` flag that prints shellcode
instead of running your command. Prefer the dedicated `completion` subcommand
for clearer UX unless you need a single-flag escape hatch.

```python
from clak import CompRenderOptMixin, Parser

class App(CompRenderOptMixin, Parser):
    def cli_run(self, **_):
        print("hello")
```

```bash
python myapp.py --completion
```

## Global argcomplete helper

To activate argcomplete for many Python CLIs system-wide (optional, once per
machine):

```bash
activate-global-python-argcomplete
```

See also [Installation](install.md).

## See also

- Planned runtime autocomplete: [Roadmap](../project/roadmap.md)
- Packaging an entry point name: [Shipping your CLI](execution.md)
