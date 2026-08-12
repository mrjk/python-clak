# Views

Clak can turn command return values into readable CLI tables (or pretty-prints)
without hand-written `print()` formatting.

## Option layers

View CLI options are layered to match the view class hierarchy. Public flag
names are stable; each option is defined once and inherited.

| Layer | Options | Who enables |
| --- | --- | --- |
| Generic (`ClakView`) | `--width` | Show, List, Pprint, Raw, Markdown, Rst |
| Table (Show + List) | `--format` (`view`/`yaml`/`json`/`csv`), `--columns`, `--sort-columns`, `--sort-mode`, `--wrap`, `--add-index` / `--no-add-index` | Show, List |
| List-only | `--expand-keys` / `--no-expand-keys` | List |
| Text (Markdown + Rst) | `--format` (`view`/`raw`) | Markdown, Rst |

Matching `Meta.view_*` defaults exist for every option (`view_width`,
`view_format`, `view_columns`, `view_sort_columns`, `view_sort_mode`,
`view_wrap`, `view_add_index`, `view_expand_keys`, plus `view_column_names`
for help text and `view_cli_options` to filter flags).

## Pick a mixin

Mix in **one** view mixin on your parser. That chooses the view and registers
matching CLI flags:

| Mixin | View | Typical data | CLI options |
| --- | --- | --- | --- |
| `ShowViewMixin` | `ShowView` | one dict / sequence | `--columns`, `--add-index` / `--no-add-index`, `--format`, `--sort-columns`, `--sort-mode`, `--width`, `--wrap` |
| `ListViewMixin` | `ListView` | list/dict of rows | `--columns`, `--add-index` / `--no-add-index`, `--expand-keys` / `--no-expand-keys`, `--format`, `--sort-columns`, `--sort-mode`, `--width`, `--wrap` |
| `PprintViewMixin` | `PprintView` | any payload | `--width` |
| `RawViewMixin` | `RawView` | plain text | `--width` |
| `MarkdownViewMixin` | `MarkdownView` | markdown source text | `--format`, `--width` |
| `RstViewMixin` | `RstView` | reStructuredText source | `--format`, `--width` |

Without a view mixin (and without returning a view / setting `Meta.cli_view`),
raw return values are **not** printed.

## Minimal example

``` python title="script_views.py" linenums="1"
--8<-- "examples/script_views.py"
```

``` raw linenums="0"
$ python script_views.py
+-------+-------+----------+
| name  | role  | city     |
+-------+-------+----------+
| ada   | admin | London   |
| linus | dev   | Helsinki |
| grace | dev   | New York |
+-------+-------+----------+

$ python script_views.py --columns name,role
+-------+-------+
| name  | role  |
+-------+-------+
| ada   | admin |
| linus | dev   |
| grace | dev   |
+-------+-------+
```

`--columns` and `--sort-columns` share the same column index syntax:

| Form | Meaning |
| --- | --- |
| `name` | column header name |
| `1` | first column |
| `2` | second column |
| `-1` | last column |
| `-3` | third from last |

Index `0` is invalid (use `1` for the first column). Example: `--columns name,role`
or `--columns 1,3` or `--columns=-1`.

List these names in help with `Meta.view_column_names` (full selectable set).
`Meta.view_columns` remains the default display subset when `--columns` is unset.

```python
class App(ListViewMixin, Parser):
    class Meta:
        view_column_names = ("name", "role", "city")
        view_columns = ("name", "role")
```

View flags appear under an **Output options** group in `--help` (same
`Argument(..., group=...)` API as any other flag; see
[Named help groups](advanced.md#named-help-groups)).

## Output format and sorting (Cliff-style)

`ShowViewMixin` and `ListViewMixin` also expose Cliff-like output controls:

| Flag | Values | Default | Effect |
| --- | --- | --- | --- |
| `--format` | `view`, `yaml`, `json`, `csv` | `view` | Render as a table or structured text |
| `--sort-columns` | `COL1,COL2,...` | first column | Sort rows (same names / 1-based / negatives as `--columns`) |
| `--sort-mode` | `asc`, `desc` | `asc` | Sort direction |
| `--width` | `min`, `auto`, `terminal` | `terminal` | View width mode (see below) |
| `--wrap` | `last`, `all` | `last` | Table column wrap when fitting (see below) |

### View width (`--width`)

Shared by show, list, pprint, and text backends (when they implement it):

| Mode | Effect on TTY | Non-TTY |
| --- | --- | --- |
| `min` | Content-sized (no wrap) | Same |
| `auto` | Content-sized; wrap if wider than the terminal | No wrap (`min`) |
| `terminal` | Always use terminal width (tables expand/wrap) | No wrap (`min`) |

Terminal size comes from `ctx.runtime` (`term_width`, honors `CLAK_COLUMNS`).
Default Meta override:

```python
class App(ListViewMixin, Parser):
    class Meta:
        view_width = "auto"  # or "min" / "terminal"
```

CLI `--width` overrides `Meta.view_width`.

### Table wrap (`--wrap`)

Table backends only (`ShowView` / `ListView`). Ignored by pprint and text
views, and ignored when width does not fit to the terminal (`min`, or non-TTY):

| Mode | Effect |
| --- | --- |
| `last` | Keep left columns content-sized; only the rightmost column wraps (default) |
| `all` | Allow any column to shrink/wrap (PrettyTable table-width redistribution) |

```python
class App(ListViewMixin, Parser):
    class Meta:
        view_wrap = "all"  # or "last"
```

CLI `--wrap` overrides `Meta.view_wrap`.

### Text views (raw / markdown / rst)

Use these when `cli_run` returns a **text** payload (not tabular data). Pick the
mixin that matches how you want it shown:

| Mixin | Default | `--format` |
| --- | --- | --- |
| `RawViewMixin` | Print source as-is | (none) |
| `MarkdownViewMixin` | Render markdown in the terminal | `view` (rendered) or `raw` (source) |
| `RstViewMixin` | Render reStructuredText | `view` (rendered) or `raw` (source) |

`--format` is **view-scoped**: table mixins use `view|yaml|json|csv`; markdown/rst
use `view|raw`. There is no conflict because a command mixes in only one view
family.

Rendered markdown needs the optional `rich` package (`pip install rich`).
Rendered RST needs `docutils` (`pip install docutils`). With `--format raw`,
no extra package is required. Missing packages raise a clear install hint.

```python
from clak import MarkdownViewMixin, Parser

class App(MarkdownViewMixin, Parser):
    def cli_run(self, **_):
        return "# Status\n\nAll **good**."
```

Example: `--sort-columns=-1,-3,1` sorts by last column, then third-from-last, then first
(use `=` when the value starts with `-`, so argparse does not treat it as a flag).

When `--sort-columns` is omitted, the **first displayed column** is sorted ascending.
Override defaults in `Meta`:

```python
class App(ListViewMixin, Parser):
    class Meta:
        view_sort_columns = ("role", "name")  # or "role,-1" or [-1, 1]
        view_sort_mode = "desc"
```

CLI flags override `Meta.view_sort_columns` and `Meta.view_sort_mode`.

``` raw linenums="0"
$ python script_views.py --format json --columns name,role
[
  {
    "name": "ada",
    "role": "admin"
  },
  {
    "name": "linus",
    "role": "dev"
  },
  {
    "name": "grace",
    "role": "dev"
  }
]

$ python script_views.py --format csv --columns name,role
name,role
ada,admin
linus,dev
grace,dev

$ python script_views.py --sort-columns name --sort-mode desc --columns name,role
+-------+-------+
| name  | role  |
+-------+-------+
| linus | dev   |
| grace | dev   |
| ada   | admin |
+-------+-------+
```

- **`view`** — PrettyTable output (default).
- **`json`** / **`csv`** — stdlib only.
- **`yaml`** — requires PyYAML (`pip install 'mrjk.clak[config]'` or `pip install pyyaml`).

Sorting applies before rendering, so it works for every format (including
multi-column sort). For List `json` / `yaml`, Clak projects and sorts the
original payload (no table fillers such as `-`); `view` / `csv` use the table
path (fillers, Index column, tab cleanup).

## Nested subcommands

View mixins on a **subcommand** parser register and apply flags on that command
(e.g. `app vars --columns name`). Hooks run for each node in the command
hierarchy, so `--format`, `--sort-columns`, and `--columns` work on nested
commands the same way as on a root parser.

```python
from clak import Command, ListViewMixin, Parser

class VarsCmd(ListViewMixin, Parser):
    def cli_run(self, **_):
        return [{"name": "ada", "role": "admin"}]

class Root(Parser):
    vars = Command(VarsCmd)
```

## Control which flags appear

Use `Meta.view_cli_options`:

| Value | Effect |
| --- | --- |
| `True` (default) | Expose all options for that mixin |
| `False` | Auto-render only — no extra flags |
| `("columns", "add_index")` | Expose a subset (`list` / `tuple` / `set` also work) |

Option names are destinations: `columns`, `add_index`, `expand_keys`, `width`,
`wrap`, `format`, `sort_columns`, `sort_mode`.
Unknown names raise `ValueError`.

```python
class App(ListViewMixin, Parser):
    class Meta:
        view_cli_options = ("columns",)  # hide --add-index / --expand-keys

    def cli_run(self, **_):
        return [{"name": "ada", "role": "admin"}]
```

## Three ways to render

=== "Mixin (recommended)"

    Return plain data; the mixin sets `cli_view` and renders automatically:

    ```python
    class App(ListViewMixin, Parser):
        def cli_run(self, **_):
            return [{"name": "ada"}, {"name": "linus"}]
    ```

=== "Return a view"

    Build the view yourself (still works with or without a mixin):

    ```python
    from clak import Parser
    from clak.views import ListView

    class App(Parser):
        def cli_run(self, **_):
            return ListView(
                [{"name": "ada"}, {"name": "linus"}],
                columns=["name"],
            )
    ```

=== "Meta.cli_view only"

    No mixin flags — configure the view class yourself:

    ```python
    from clak import Parser
    from clak.views import ListView

    class App(Parser):
        class Meta:
            cli_view = ListView

        def cli_run(self, **_):
            return [{"name": "ada"}, {"name": "linus"}]
    ```

## CLI overrides

When a mixin is present, CLI flags merge into `.render(**kwargs)`.

- **CLI wins** over values set on a returned `ClakView(...)`.
- If CLI overrides an already-set view option, Clak logs a **warning**.

```python
class App(ListViewMixin, Parser):
    def cli_run(self, **_):
        # columns=["name","role"] can be overridden by --columns name
        return ListView(rows, columns=["name", "role"])
```

## Show vs list vs pprint

- **Show** — one record as key/value (or index/value) rows.
- **List** — many records as a multi-column table (`expand_keys` flattens nested dicts).
- **Pprint** — `pprint`-style dump with shared `--width` modes.

API details: [Views component](../api/plugin_views.md).
