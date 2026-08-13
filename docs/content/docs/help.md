# Colored `--help`

`--help` is colored by default when Rich is installed and stdout is a TTY.
No mixin and no CLI flags. Layout stays argparse
(`RecursiveHelpFormatter`: command tree, defaults, option names). Color is
applied after wrap.

```python
from clak import Parser

class App(Parser):
    """Demo application."""

    def cli_run(self, **_):
        return None
```

Needs `pip install 'mrjk.clak[markdown]'` (Rich). Missing Rich, a non-TTY
stdout, `NO_COLOR`, `CLAK_COLORS=0`, or `CLAK_COLOR_BACKEND=none` keep the
same plain text as `RecursiveHelpFormatter`.

Opt out per command:

```python
from clak import Parser, RecursiveHelpFormatter

class App(Parser):
    class Meta:
        help_formatter = RecursiveHelpFormatter
```

A child inherits the root formatter. After a parent opt-out, a child can
re-opt-in with `RichHelpMixin` (left of `Parser`).

`help_description` and `help_epilog` accept Rich markup when color is on
(`[bold]Name[/bold]`). Argument `help=` stays literal. CompositeView section
`title` / `description` use the same markup helper; see
[Views](views.md#multiple-sections-compositeview).

API: [Help component](../api/plugin_help.md).
