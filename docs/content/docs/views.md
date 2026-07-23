# Views

Clak can turn command return values into readable CLI tables (or pretty-prints)
without hand-written `print()` formatting.

## Pick a mixin

Mix in **one** view mixin on your parser. That chooses the view and registers
matching CLI flags:

| Mixin | View | Typical data | CLI options |
| --- | --- | --- | --- |
| `ShowViewMixin` | `ShowView` | one dict / sequence | `--columns`, `--add-index` / `--no-add-index`, `--format`, `--sort-columns`, `--sort-mode` |
| `ListViewMixin` | `ListView` | list/dict of rows | `--columns`, `--add-index` / `--no-add-index`, `--expand-keys` / `--no-expand-keys`, `--format`, `--sort-columns`, `--sort-mode` |
| `PprintViewMixin` | `PprintView` | any payload | `--width` |

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

`--columns` is a **comma-separated** list (`name,role` or indexes like `0,2`).

## Output format and sorting (Cliff-style)

`ShowViewMixin` and `ListViewMixin` also expose Cliff-like output controls:

| Flag | Values | Default | Effect |
| --- | --- | --- | --- |
| `--format` | `view`, `yaml`, `json`, `csv` | `view` | Render as a table or structured text |
| `--sort-columns` | `COL1,COL2,...` | first column | Sort rows (names, **1-based** indexes, or **negative** from end: `-1`=last) |
| `--sort-mode` | `asc`, `desc` | `asc` | Sort direction |

Index syntax for `--sort-columns`:

| Form | Meaning |
| --- | --- |
| `name` | column header name |
| `1` | first column |
| `2` | second column |
| `-1` | last column |
| `-3` | third from last |

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

Sorting applies before rendering, so it works for every format (including multi-column sort).

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
`format`, `sort_columns`, `sort_mode`.
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
- **Pprint** — `pprint`-style dump with optional `--width`.

API details: [Views component](../api/plugin_views.md).
