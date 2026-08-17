# Colored `--help`

`--help` is colored by default when Rich is installed and stdout is a TTY.
No mixin and no CLI flags. Layout stays argparse
(`RecursiveHelpFormatter`: subcommand list, defaults, option names). Color is
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

`--help` lists nested subcommands by default (`Meta.help_subcommands = "all"`).
Nested names hide the parent path (`Meta.help_hide_parent = True`):

```text
subcommands:
  tool                 Tools
    netmap             Map networks
  var                  Vars
    ls                 List vars
```

Set `help_subcommands = "top"` to list only immediate children. Set
`help_hide_parent = False` to keep flattened paths (`tool netmap`).
A child inherits these settings and may override. Independent of grouping.
An empty `positional arguments:` heading (subcommands only, no NAME-style
args) is omitted.

```python
class App(Parser):
    class Meta:
        help_subcommands = "top"  # optional: immediate children only
        help_hide_parent = False  # optional: show "tool netmap" paths
```

Subcommand sections (`Meta.command_groups` + `Command(..., command_group=)`)
are layout on that command only. Do not set `Meta.help_formatter` just to
group children or change listing depth; those are Meta layout, not a
formatter class. See
[Named help groups](advanced.md#named-help-groups-and-exclusive-groups).

`help_description` and `help_epilog` accept Rich markup when color is on
(`[bold]Name[/bold]`). Argument `help=` stays literal. RST ``literals`` are
stripped from rendered `--help` (not converted to Rich). Argument `help=` is
included because the formatter strips the full text. CompositeView section
`title` / `description` use the same markup helper; see
[Views](views.md#multiple-sections-compositeview).

API: [Help component](../api/plugin_help.md).
