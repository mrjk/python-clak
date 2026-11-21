# Changelog

## Unreleased

### Added

- `ApiServerMixin`, `ApiEndpointMixin` and `ApiServeCmd` (POC): serve opted-in
  commands over HTTP (`POST /path/to/cmd`, JSON body), optional basic auth,
  pluggable drivers (FastAPI first, extra `api`).
- Table views (`ShowView`, `ListView`, `CompositeView`) render list/dict
  cells as block YAML by default. If a value can't be dumped (or PyYAML is
  missing), the original value is shown unchanged. This only affects
  `--format view`; yaml/json/csv output is untouched. Opt out with
  `--no-yaml-cells`, `Meta.view_yaml_cells = False`, or `yaml_cells=False`.

### Changed (breaking)

Internal cleanup; most of this is semi-public surface.

| Before | After |
| --- | --- |
| `ParserNode.show_epilog()` | removed (it called a method argparse does not have) |
| `query_cfg_*(report=, override=, raise_on_undeclared=)`, `Node.get_name`, `Fn`, `NullType`/`NotSet`/`UnSetArg`/`UNSET_ARG` | removed; one `NOT_SET` marker |
| `clak.core.nodes.ConfigurationError` / `MissingMetaError` | `clak.exception` |
| `FormatEnv`, `SubParser.meta__help_flags/usage/description/epilog` | removed (`prepare_docstring` wraps `self` itself) |
| `ErrorRenderer`, `ArgumentParser(error_renderer=)`, unused `ArgparseCapabilities` flags | module functions in `clak.core.argp.errors`; flags removed |
| `Terminator` | `clak.core._exception.clean_terminate()` |
| `PluginStore`, `DataStore` | plain `dict` (`ctx.plugins`, `ctx.data`) |
| `clak.core.plugins`, `clak.core` re-exports of internals, most of `clak.runtime` re-exports | `CLI_HOOK_PREFIX` in `clak.core.parser`; import from submodules |
| `LoggingOptMixin.test_logger()` | removed |
| `ctx.facts` built on every dispatch | built on first access; `clak.runtime.facts` is smaller (same API) |
| `clak.comp.help.RichRecursiveHelpFormatter`, `help_document_colorizer` | `clak.core.help_render` |
| `ui_policy`, `ui_session`, `set_ui_settings` in `clak.comp.runtime` | `clak.comp.ui` (still exported from `clak.comp`) |
| column/sort helpers in `clak.views.table` / `table_formatter`; `require_yaml` | `clak.views.columns`; `clak.views.serialize` |
| `ClakView._render()` / `_output()`, per-view `render()` | implement `to_text(payload, settings)`; `render()` is shared |
| `require_rich`, `require_docutils`, `require_rich_for_data`, `_yaml`/`coloredlogs` module sentinels | `clak._optional.require()` / `optional()` |

### Fixed

- `ObjectNamespace` stored a stray `__dict__` key, which leaked into
  `cli_run`/`cli_group` kwargs and `len()`.
- `CompositeView(width="fit")` never shrank equalized tables to the terminal
  (it compared against a mode name that no longer exists).
- The prettytable/ColorTable choice is made at render time, so
  `ClakSettings.set_current()` is honored.

## 0.7.0a1

Alpha of the 0.7 architecture cleanup. Several **breaking changes**; see
"Upgrading" below.

### Upgrading

| Before | After |
| --- | --- |
| `from clak.parser import ...`, `clak.nodes`, `clak.descriptors`, `clak.settings`, `clak.plugins`, `clak.facts`, `clak.log_levels`, `clak.table_formatter`, `clak.argparse_` | `from clak import ...`, or the real module under `clak.core.*`, `clak.runtime.*`, `clak.views.*` |
| `clak.views.rich_style`, `clak.core.argparse_` | `clak.runtime.rich_style`, `clak.core.argp` / `clak.core.help_render` |
| `ArgumentParser`, `SubCommand`, `Cmd`, `ArgumentParserPlus` | `Parser`, `Command` (class: `SubParser`), `clak.core.argp.ArgumentParser` |
| `PluginHelpers.hook_register(...)`, `ctx.cli_methods` | define `cli_hook__<name>(self, instance, ctx, **_)` on a mixin |
| `clak.runtime.CLAK_COLORS` / `CLAK_DEBUG` / `CLAK_LOG_COLORS` | `ClakSettings.current().colors` / `.debug` / `.log_colors`; override with `ClakSettings.set_current(...)` (env var names unchanged) |
| `clak.views.base.merge_view_settings`, `resolve_wrap_budget` | `ClakView.merge_settings`, `resolve_line_length` |
| `Meta.abbrev_commands` defaulted to `False` | defaults to `True`; set `False` to require full command names |

### Changed

- Unique subcommand prefixes are accepted by default (`app s bu` runs
  `app sub buzz`), like long flags already were. Ambiguous prefixes still
  error and exact names always win.
- A subcommand's own `Meta` now overrides settings declared by a mixin on
  an ancestor (e.g. `Meta.view_columns`, `Meta.log_suffix` on a plain
  subcommand under a `ListViewMixin` / `LoggingOptMixin` root), and an
  ancestor's `Meta.view_*` reaches a child that uses the same view mixin.
- `NO_COLOR` also disables auto-colored logs (explicit `--log-colors` /
  `CLAK_LOG_COLORS` still win).
- `--help` width honors `CLAK_COLUMNS`, like `ctx.runtime`.
- UI components without a policy apply the `CI` check of
  `detect_interactive()`.
- View options are declared once in a `ViewOption` registry
  (`clak.comp.views`); mixins list theirs in `_view_options`.
- Dispatch / terminate log under `clak.core._dispatch` /
  `clak.core._exception`.

### Fixed

- Shared class-level `Argument` descriptors were mutated when attached to
  a parser.
- `Parser(False)` passed `False` to `dispatch()` as argv.
- `ctx` / `ctx.args` (`ObjectNamespace`) can be copied and pickled.

### Performance

- `import clak` is about 2x faster (~85 ms instead of ~175-240 ms): rich,
  PyYAML, argcomplete, coloredlogs and `importlib.metadata` are imported on
  first use.
