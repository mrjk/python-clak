# Plugins

Clak features are optional. Each one is a **mixin class**: you list it before
`Parser` in your class bases, and it brings its flags, its `Meta` settings and
the code that acts on them.

``` python
from clak import LoggingOptMixin, RuntimeOptMixin, ListViewMixin, Parser

class App(LoggingOptMixin, RuntimeOptMixin, Parser):
    """My app."""

class UserList(ListViewMixin, Parser):
    """List users."""
```

Always put mixins **before** `Parser`: Python resolves methods left to right,
and mixins override `Parser` hooks such as `_prepare_argument`.

## How a mixin works

A mixin is a plain class that can contain:

| Element | Effect |
| --- | --- |
| `Argument` class attributes | Become flags of the parser, exactly like your own arguments. |
| `meta__config__<name> = MetaSetting(help=...)` | Declares a `Meta.<name>` setting (documentation and validation). |
| `meta__<name> = value` | Default value of that setting. Users override it in `Meta`. |
| `cli_hook__<name>(self, instance, ctx, **_)` | Hook run during dispatch, before `cli_group` / `cli_run`. |
| `_prepare_argument(self, key, arg)` | Adjusts an argument before it is attached (inject a default, format help). |
| `_skip_argument_names(self)` | Hides some argument attributes (used by view mixins to filter flags). |

### Hooks

Hooks are collected by name prefix (`cli_hook__`) when the parser is built.
During dispatch, Clak walks the command path from the root to the selected
command. At each step it adds the hooks of the current command to those
already collected, then runs all of them. A hook defined on the root therefore
runs once per level; use `ctx.cli_first` for work that must happen only once.

A hook usually reads `ctx.args`, then publishes its result in
`ctx.plugins["<name>"]` and/or as a `ctx` attribute, so commands and other
mixins can use it.

### Writing your own mixin

``` python title="my_mixins.py"
from clak import Opt, Parser


class DryRunMixin:
    """Add --dry-run and publish it on ctx."""

    dry_run = Opt("--dry-run", action="store_true", help="Do not change anything")

    def cli_hook__dry_run(self, instance, ctx, **_):
        if ctx.cli_first:
            ctx.dry_run = ctx.args.dry_run
            ctx.plugins["dry_run"] = ctx.dry_run


class App(DryRunMixin, Parser):
    def cli_run(self, ctx, **_):
        if ctx.dry_run:
            print("Nothing changed")
```

Since flags propagate to subcommands, a mixin set on the root makes its flags
available on every command. Opt out per flag with `propagate=False`.

## Available mixins

All mixins are importable from `clak` (and from `clak.comp`).

!!! note "Hand maintained"
    These tables are maintained by hand. When a mixin gains or loses a flag
    or a `Meta` setting, update them. The source of truth is `clak/comp/`.

### Feature mixins

| Mixin | Flags | `Meta` settings | Publishes on `ctx` | Page |
| --- | --- | --- | --- | --- |
| `LoggingOptMixin` | `-v`/`--verbose` (count), `--log-format {default,extended,audit,debug}`, `--trace` / `--no-trace`, `--log-colors` / `--no-log-colors` | `log_prefix`, `log_suffix`, `log_default_level`, `log_levels`, `log_silent`, `log_colors_env` (default `CLAK_LOG_COLORS`) | `self.logger` | [Logging](logging.md) |
| `RuntimeOptMixin` | `--interactive {auto,always,never}`, `--no-input`, `-y`/`--yes` | - | `ctx.interactive`, `ctx.assume_yes`, `ctx.plugins["runtime"]`, `ctx.plugins["ui_settings"]` | [Batch mode](unattended.md) |
| `XDGConfFileMixin` | `--conf-file` (default `$XDG_CONFIG_HOME/<app>/config.yaml`) | `app_name`, `config_required`, `config_local_names` | `ctx.config`, `ctx.plugins["config"]`, `ctx.plugins["config_path"]`, `cli_root.config` | [Config](config.md) |
| `XDGDataDirMixin` | `--data-dir` (default `$XDG_DATA_HOME/<app>`) | `app_name` | `ctx.args.data_dir` | [Config](config.md) |
| `XDGCacheDirMixin` | `--cache-dir` (default `$XDG_CACHE_HOME/<app>`) | `app_name` | `ctx.args.cache_dir` | [Config](config.md) |
| `XDGLogDirMixin` | `--log-dir` (default `$XDG_CACHE_HOME/<app>/logs`) | `app_name` | `ctx.args.log_dir` | [Config](config.md) |
| `WorkDirMixin` | `-W`/`--work-dir` | - | `ctx.work_dir`, `ctx.plugins["work_dir"]` (also changes the process cwd) | [Config](config.md) |
| `ApiServerMixin` | - (use `ApiServeCmd` for `--host`, `--port`, `--auth-user`, `--auth-password`) | `api_host`, `api_port`, `api_driver`, `api_auth_user`, `api_auth_password` | - | - |
| `ApiEndpointMixin` | - | `api_path` | - | - |
| `RichHelpMixin` | - | sets `help_formatter` to the Rich formatter | - | [Help](help.md) |
| `CompRenderOptMixin` | `--completion` (prints bash completion code) | - | - | [Completion](completion.md) |
| `CompRenderCmdMixin` | `-s`/`--shell {bash,zsh,tcsh,fish,powershell}`, `--no-defaults`, `--complete-arguments ...` (hidden: `--executable`, `-e`/`--external-argcomplete-script`) | - | - | [Completion](completion.md) |

`CompCmdRender` is a ready-made `CompRenderCmdMixin` + `Parser` command:
attach it with `completion = Command(CompCmdRender)`.

`ApiServerMixin` (root) and `ApiEndpointMixin` (commands to expose, opt-in)
serve the CLI over HTTP: `app users add` becomes `POST /users/add`, the JSON
body maps argument names to values and is validated by the command's own
parser (422 on bad input, 400 on `ClakUserError`). Attach the ready-made
`serve = Command(ApiServeCmd)`. Needs `pip install 'mrjk.clak[api]'`; backends
are pluggable through `clak.comp.api.API_DRIVERS` (`fastapi` ships first).
See `examples/script_api.py`.

Rich help is already the `Parser` default; `RichHelpMixin` only re-enables it
on a branch where a parent set `Meta.help_formatter = RecursiveHelpFormatter`.

### View mixins

A view mixin picks the view that renders the return value of `cli_run`, and
adds the matching output flags (in the `Output options` help section). Use one
per command.

| Mixin | View | Flags | `Meta` defaults |
| --- | --- | --- | --- |
| `ShowViewMixin` | `ShowView` | `--columns`, `--add-index` / `--no-add-index`, `--format {view,yaml,json,csv}`, `--sort-columns`, `--sort-mode {asc,desc}`, `--width {content,fit,terminal}`, `--wrap` | `view_columns`, `view_column_names`, `view_add_index`, `view_format`, `view_sort_columns`, `view_sort_mode`, `view_width`, `view_wrap`, `view_wrap_min` |
| `ListViewMixin` | `ListView` | Show flags + `--expand-keys` / `--no-expand-keys` | Show settings + `view_expand_keys` |
| `PprintViewMixin` | `PprintView` | `--line-length` | `view_line_length` |
| `RawViewMixin` | `RawView` | `--line-length` | `view_line_length` |
| `MarkdownViewMixin` | `MarkdownView` | `--format {view,raw}`, `--line-length` | `view_format`, `view_line_length`, `view_syntax_theme` |
| `RstViewMixin` | `RstView` | `--format {view,raw}`, `--line-length` | `view_format`, `view_line_length` |
| `DataViewMixin` | `DataView` | `--format {json,yaml}`, `--compact` / `--no-compact`, `--color` / `--no-color`, `--anchors` / `--no-anchors` | `view_format`, `view_compact`, `view_color`, `view_anchors`, `view_syntax_theme` |
| `CompositeViewMixin` | none: return a `CompositeView` | Show flags + `--expand-keys` / `--no-expand-keys`, `--format-scope {first,all}`, `--line-length` | Show settings + `view_expand_keys`, `view_format_scope`, `view_line_length` |

Every view mixin also accepts `Meta.view_cli_options`: `True` (all flags,
default), `False` (no flags) or a list of flag destinations to expose, for
example `("columns", "format")`. `Meta.view_*` defaults only apply to exposed
flags.

The collected settings are published as `ctx.view_settings` (and
`ctx.plugins["view_settings"]`).

## Views

Views are the classes that turn a payload into text. A view mixin uses one
automatically, but you can also use views directly: return an instance from
`cli_run` (CLI flags are merged over its settings), set `Meta.cli_view`, or call
`render()` yourself.

``` python
from clak.views import ShowView

def cli_run(self, **_):
    return ShowView({"name": "ada", "role": "admin"}, width="content")
```

`view.render(payload=None, stdout=True, **settings)` prints the result (unless
`stdout=False`) and returns the rendered string.

All views are importable from `clak.views`.

| View | Payload | Settings (default) | Extra dependency |
| --- | --- | --- | --- |
| `ClakView` | - | Base class: holds `payload` and `settings`, merges `settings_default` < constructor settings < `render()` settings. | - |
| `TableView` | - | Base of Show and List: `columns` (None), `width` (`fit`), `wrap` (`last`), `wrap_min` (None), `format` (`view`), `sort_columns` (None), `sort_mode` (`asc`), `add_index` (None) | - |
| `ShowView` | one dict or sequence (key/value table) | TableView settings, `add_index` (`True`) | YAML for `format=yaml` |
| `ListView` | list or dict of rows | TableView settings, `expand_keys` (`True`), `add_index` (None) | YAML for `format=yaml` |
| `PprintView` | any Python object | `line_length` (120) | - |
| `RawView` | text | `line_length` (120) | - |
| `MarkdownView` | Markdown source | `line_length` (120), `format` (`view`/`raw`), `theme` (None) | `mrjk.clak[markdown]` (Rich) |
| `RstView` | reStructuredText source | `line_length` (120), `format` (`view`/`raw`) | `mrjk.clak[rst]` (docutils) |
| `DataView` | any structured data | `format` (None: yaml if PyYAML is installed, else json), `compact` (`False`), `color` (None: auto), `anchors` (`True`), `theme` (None) | `mrjk.clak[config]` for YAML, Rich for color |
| `CompositeView` | ordered sections (tables and/or text) | TableView settings, `expand_keys` (`True`), `format_scope` (`first`), `primary` (constructor: primary section name) | - |

Accepted values:

| Setting | Values |
| --- | --- |
| `width` | `content` (size to data), `fit` (shrink to terminal), `terminal` (full width). Aliases: `min`, `auto`. |
| `wrap` | `last`, `first`, `all`, or column names/indexes in priority order. |
| `line_length` | positive int, `terminal`, or `nowrap`. |
| `columns`, `sort_columns` | names, 1-based indexes, or negative indexes (`-1` = last); comma-separated string or sequence. |
| `format_scope` | `first` (primary section only) or `all` (envelope of every section). |

Wrapping only applies when stdout is a terminal. For details and examples, see
[Views](views.md).
