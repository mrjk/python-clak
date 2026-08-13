# Rich `--help`

Default `Parser` help is plain argparse. Opt in to colored `--help` with
`RichHelpMixin`. No CLI flags.

```python
from clak import Parser, RichHelpMixin

class App(RichHelpMixin, Parser):
    """Demo application."""

    def cli_run(self, **_):
        return None
```

Put the mixin left of `Parser`, same as logging and views. A root mixin
applies to nested commands. A child can opt out:

```python
from clak import Parser, RecursiveHelpFormatter, RichHelpMixin

class Child(Parser):
    class Meta:
        help_formatter = RecursiveHelpFormatter
```

Needs `pip install 'mrjk.clak[markdown]'` (Rich). Missing Rich, a non-TTY
stdout, `CLAK_COLORS=0`, or `CLAK_COLOR_BACKEND=none` keep the same plain
text as without the mixin.

`help_description` and `help_epilog` accept Rich markup when color is on
(`[bold]Name[/bold]`). Argument `help=` stays literal. CompositeView section
`title` / `description` use the same markup helper without this mixin; see
[Views](views.md#multiple-sections-compositeview).

API: [Help component](../api/plugin_help.md).
