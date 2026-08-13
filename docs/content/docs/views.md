# Views

Clak can turn command return values into readable CLI tables (or pretty-prints)
without hand-written `print()` formatting.

## Option layers

View CLI options are layered to match the view class hierarchy. Public flag
names are stable; each option is defined once and inherited.

| Layer | Options | Who enables |
| --- | --- | --- |
| Generic (`ClakView`) | (none) | - |
| Table (Show + List) | `--width` (`content`/`fit`/`terminal`), `--format` (`view`/`yaml`/`json`/`csv`), `--columns`, `--sort-columns`, `--sort-mode`, `--wrap`, `--add-index` / `--no-add-index` | Show, List, Composite |
| List-only | `--expand-keys` / `--no-expand-keys` | List, Composite |
| Text layout | `--line-length` (`N`/`terminal`/`nowrap`) | Raw, Pprint, Markdown, Rst, Composite |
| Text (Markdown + Rst) | `--format` (`view`/`raw`) | Markdown, Rst |
| Data | `--format` (`json`/`yaml`), `--compact` / `--no-compact`, `--color` / `--no-color`, `--anchors` / `--no-anchors` | Data |
| Composite | `--format-scope` (`first`/`all`) | Composite |

Matching `Meta.view_*` defaults exist for every option (`view_width`,
`view_line_length`, `view_format`, `view_format_scope`, `view_columns`,
`view_sort_columns`, `view_sort_mode`, `view_wrap`, `view_wrap_min`,
`view_add_index`, `view_expand_keys`, `view_compact`, `view_color`,
`view_anchors`, `view_syntax_theme`, plus `view_column_names` for help text and
`view_cli_options` to filter flags).

## Pick a mixin

Mix in **one** view mixin on your parser. That chooses the view and registers
matching CLI flags:

| Mixin | View | Typical data | CLI options |
| --- | --- | --- | --- |
| `ShowViewMixin` | `ShowView` | one dict / sequence | `--columns`, `--add-index` / `--no-add-index`, `--format`, `--sort-columns`, `--sort-mode`, `--width`, `--wrap` |
| `ListViewMixin` | `ListView` | list/dict of rows | `--columns`, `--add-index` / `--no-add-index`, `--expand-keys` / `--no-expand-keys`, `--format`, `--sort-columns`, `--sort-mode`, `--width`, `--wrap` |
| `PprintViewMixin` | `PprintView` | any payload | `--line-length` |
| `DataViewMixin` | `DataView` | any structured payload | `--format`, `--compact` / `--no-compact`, `--color` / `--no-color`, `--anchors` / `--no-anchors` |
| `RawViewMixin` | `RawView` | plain text | `--line-length` |
| `MarkdownViewMixin` | `MarkdownView` | markdown source text | `--format`, `--line-length` |
| `RstViewMixin` | `RstView` | reStructuredText source | `--format`, `--line-length` |
| `CompositeViewMixin` | (return `CompositeView`) | primary table + extras | table flags + `--expand-keys` + `--format-scope` + `--line-length` |

Without a view mixin (and without returning a view / setting `Meta.cli_view`),
raw return values are **not** printed. `CompositeViewMixin` does not set
`Meta.cli_view`; return a `CompositeView(...)` from `cli_run`.

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
`Argument(..., option_group=...)` API as any other flag; see
[Named help groups](advanced.md#named-help-groups-and-exclusive-groups)).

## Output format and sorting (Cliff-style)

`ShowViewMixin` and `ListViewMixin` also expose Cliff-like output controls:

| Flag | Values | Default | Effect |
| --- | --- | --- | --- |
| `--format` | `view`, `yaml`, `json`, `csv` | `view` | Render as a table or structured text |
| `--sort-columns` | `COL1,COL2,...` | first column | Sort rows (same names / 1-based / negatives as `--columns`) |
| `--sort-mode` | `asc`, `desc` | `asc` | Sort direction |
| `--width` | `content`, `fit`, `terminal` | `terminal` | Table width mode (see below) |
| `--wrap` | `last`, `first`, `all`, or `COL,...` | `last` | Which columns are flexible (see below) |

### Table width (`--width`)

Table backends only (`ShowView` / `ListView` / `CompositeView` tables). Text
views use `--line-length` instead.

| Mode | Effect on TTY | Non-TTY |
| --- | --- | --- |
| `content` | Size to data (no wrap) | Same |
| `fit` | Size to data; wrap if wider than the terminal | No wrap (`content`) |
| `terminal` | Always use the terminal width (tables expand/wrap) | No wrap (`content`) |

Aliases `min` -> `content` and `auto` -> `fit` still work in Meta and when
passed to a view constructor. Help shows the new names only.

Terminal size comes from `ctx.runtime` (`term_width`, honors `CLAK_COLUMNS`).
Default Meta override:

```python
class App(ListViewMixin, Parser):
    class Meta:
        view_width = "fit"  # or "content" / "terminal"
```

CLI `--width` overrides `Meta.view_width`.

### Table wrap (`--wrap`)

Table backends only (`ShowView` / `ListView`). Ignored by pprint and text
views, and ignored when width does not fit to the terminal (`content`, or non-TTY).

`--wrap` names the **flexible columns**: they expand or reduce to match the
available terminal space. Every other column stays at its natural content width.

- Too wide: flexible columns shrink, in listed order, until the table fits.
- Spare space (`width=terminal`): the first flexible column grows to fill it.

| Value | Flexible columns |
| --- | --- |
| `last` | Rightmost column only (default) |
| `first` | Leftmost column only |
| `all` | Any column (PrettyTable redistributes; short cells may wrap) |
| `Path,Src` | Those columns, in order (same names / 1-based / negatives as `--columns`) |

`Meta.view_wrap_min` (or constructor `wrap_min`) is the shrink floor: a positive
int for every flexible column, or a `{column: int}` map. Default floor is the
header length. There is no CLI flag for min width. If the terminal is still too
narrow, leftover dumps onto the last flexible column (down to 1 character).

```python
class App(ListViewMixin, Parser):
    class Meta:
        view_wrap = ("Path", "Src")  # Path flexes first, then Src
        view_wrap_min = {"Path": 24, "Src": 12}
```

CLI `--wrap Path,Src` overrides `Meta.view_wrap`. Use `--wrap=-1` when the value
starts with `-`.

### Text views (raw / markdown / rst)

Use these when `cli_run` returns a **text** payload (not tabular data). Pick the
mixin that matches how you want it shown:

| Mixin | Default | `--format` | `--line-length` |
| --- | --- | --- | --- |
| `RawViewMixin` | Print source as-is | (none) | wrap at 120 (or `terminal` / `nowrap`) |
| `MarkdownViewMixin` | Render markdown in the terminal | `view` (rendered) or `raw` (source) | same |
| `RstViewMixin` | Render reStructuredText | `view` (rendered) or `raw` (source) | same |

`--line-length` wraps prose at N columns (default 120, or the terminal if
narrower), `terminal` (full terminal width), or `nowrap` (do not wrap). No wrap
when stdout is not a TTY.

```python
class App(MarkdownViewMixin, Parser):
    class Meta:
        view_line_length = 80  # or "terminal" / "nowrap"
```

CLI `--line-length` overrides `Meta.view_line_length`.

`--format` is **view-scoped**: table mixins use `view|yaml|json|csv`; markdown/rst
use `view|raw`. There is no conflict because a command mixes in only one view
family.

Rendered markdown needs `pip install 'mrjk.clak[markdown]'` (`rich`).
Color is foreground-only: no black chips on inline code or fenced blocks, and
fenced `yaml` / `json` use the same Syntax theme as DataView
(`MarkdownView(theme=...)` > `Meta.view_syntax_theme` > `CLAK_SYNTAX_THEME` >
`ansi_dark`). Rendered RST needs `pip install 'mrjk.clak[rst]'` (`docutils`).
With `--format raw`, no extra package is required. Missing packages raise a
clear install hint.

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
`wrap`, `format`, `format_scope`, `sort_columns`, `sort_mode`, `line_length`.
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

## Multiple sections (CompositeView)

When a command needs a **primary table** plus extras (other tables, markdown,
raw text), return a `CompositeView` of named sections:

```python
from clak import CompositeViewMixin, Parser
from clak.views import CompositeView, ListView, MarkdownView

class App(CompositeViewMixin, Parser):
    def cli_run(self, **_):
        return CompositeView(
            [
                ("users", ListView([{"name": "ada", "role": "admin"}])),
                ("notes", MarkdownView("## Notes\nMore detail.")),
                ("related", ListView([{"name": "linus"}])),
            ]
        )
```

Optional per-section `title` and `description` (third-item dict).
The section name stays the machine id (`primary=`, envelope); titles are
opt-in and are not inferred from the name. In human view, title and
description are Rich markup when `CLAK_COLOR_BACKEND` is `auto` (and rich is
installed) or `rich` (`[bold]Users[/bold]`). The `===` chrome is dimmed when
Rich is on. Machine json/yaml/csv keep the
raw strings. `CLAK_COLOR_BACKEND=none` prints tags as-is. The same markup
helper is used by `RichHelpMixin` for `--help` description/epilog; CompositeView
does not require that mixin.

```python
CompositeView(
    [
        (
            "users",
            ListView([{"name": "ada", "role": "admin"}]),
            {
                "title": "Users",
                "description": "People with access to this project.",
            },
        ),
        ("notes", MarkdownView("## Notes\nMore detail."), {"title": "Notes"}),
        ("related", ListView([{"name": "linus"}])),
    ]
)
```

Human view prints `=== Users ===`, then the description, then the child view.
Untitled sections keep the previous look (blank line only).

Human (`--format view`) output prints sections in order, separated by a blank
line. Table sections share the same outer width (equalized under `--width content`
/ `fit`; shared terminal budget under `--width terminal`). Text sections follow
`--line-length` (default 120) and are not stretched to the table border.

Table CLI flags (`--columns`, `--sort-*`, `--add-index`, ...) apply to the
**primary** section only (first section by default; override with
`CompositeView(..., primary="related")`). `--expand-keys` is always registered
(for a ListView primary); omit `expand_keys` from `Meta.view_cli_options` when
the primary is ShowView.

`--format` is **table-scoped** (`view` / `yaml` / `json` / `csv`). There is no
`--format raw` for markdown or RST inside a composite; source text is in the
`--format-scope all` envelope `data` field.

### Machine formats (`--format-scope`)

| Scope | Effect |
| --- | --- |
| `first` (default) | Export only the primary section (same shape as a lone List/Show) |
| `all` | Export an envelope of every section |

```python
class App(CompositeViewMixin, Parser):
    class Meta:
        view_format_scope = "all"  # or "first"
```

CLI `--format-scope first|all` overrides Meta. Envelope shape for json/yaml:

```json
{
  "sections": [
    {"name": "users", "kind": "list", "title": "Users", "data": [ ... ]},
    {"name": "notes", "kind": "markdown", "data": "## Notes\n..."}
  ]
}
```

`title` and `description` appear in the envelope only when set. CSV with
`--format-scope all` emits sequential blocks separated by a blank line, each
starting with `# section: <name>` and optional `# title:` / `# description:`
comments.

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

## Show vs list vs pprint vs data vs composite

- **Show** — one record as key/value (or index/value) rows.
- **List** — many records as a multi-column table (`expand_keys` flattens nested dicts).
- **Pprint** — `pprint`-style dump with `--line-length` (debug-oriented).
- **Data** — structured JSON/YAML dump of any payload (see below).
- **Composite** — ordered sections (tables and/or text) with shared table width,
  `--line-length` for prose, and optional machine envelope via `--format-scope`.

### DataView options

`DataViewMixin` serializes the command return value as JSON or YAML:

| Flag | Default | Notes |
| --- | --- | --- |
| `--format json\|yaml` | auto | YAML when PyYAML is installed, else JSON. Explicit `yaml` without PyYAML fails with install advice. |
| `--compact` / `--no-compact` | off | JSON only: single-line vs indented. |
| `--color` / `--no-color` | auto | Colorize with rich when `CLAK_COLORS`, TTY, and rich are available. Explicit `--color` without rich fails. Color is foreground-only; the terminal background is left as-is (no theme pane or token fill). |
| `--anchors` / `--no-anchors` | on | YAML only: keep or disable anchors/aliases for shared references. |

Syntax theme (no CLI flag; shared with MarkdownView code fences):
`DataView(theme=...)` / `MarkdownView(theme=...)` > `Meta.view_syntax_theme` >
`CLAK_SYNTAX_THEME` > `ansi_dark`. Invalid names fail via rich/Pygments.
Color is foreground-only; the terminal background is left as-is.

Extras: `mrjk.clak[config]` for YAML, `mrjk.clak[markdown]` for rich colors.

API details: [Views component](../api/plugin_views.md).
