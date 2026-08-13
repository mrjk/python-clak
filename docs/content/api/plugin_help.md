# Help

`--help` is colored by default when Rich is installed and stdout is a TTY.
Opt out with `Meta.help_formatter = RecursiveHelpFormatter`.
`RichHelpMixin` is optional (re-opt-in after a parent opt-out).
Full walkthrough: [Colored help](../docs/help.md).

```python
from clak import Parser

class App(Parser):
    class Meta:
        help_description = "Hello [bold]World[/bold]"
        help_epilog = "See the docs."

    def cli_run(self, **_):
        return None
```

No CLI flags. Color follows TTY stdout, `NO_COLOR`, `CLAK_COLORS`, and
`CLAK_COLOR_BACKEND`. Install Rich with `pip install 'mrjk.clak[markdown]'`.

::: clak.comp.help
    options:
      show_source: false
      members:
        - RichHelpMixin
        - RichRecursiveHelpFormatter
        - help_uses_rich
