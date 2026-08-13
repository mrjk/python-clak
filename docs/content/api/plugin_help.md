# Help

Add `RichHelpMixin` for colored `--help`. Omit it for plain argparse help.
Full walkthrough: [Rich help](../docs/help.md).

```python
from clak import Parser, RichHelpMixin

class App(RichHelpMixin, Parser):
    class Meta:
        help_description = "Hello [bold]World[/bold]"
        help_epilog = "See the docs."

    def cli_run(self, **_):
        return None
```

No CLI flags. Color follows TTY stdout, `CLAK_COLORS`, and
`CLAK_COLOR_BACKEND`. Install Rich with `pip install 'mrjk.clak[markdown]'`.

::: clak.comp.help
    options:
      show_source: false
      members:
        - RichHelpMixin
        - RichRecursiveHelpFormatter
        - help_uses_rich
