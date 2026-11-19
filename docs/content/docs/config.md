# Config

Clak provides one opt-in mixin per XDG Base Directory path flag. Most apps
only need `XDGConfFileMixin`, which adds `--conf-file` and loads the file once
during dispatch.

API reference: [Config component](../api/plugin_config.md).

## Quick start

```python
from clak import Parser, XDGConfFileMixin

class App(XDGConfFileMixin, Parser):
    class Meta:
        app_name = "cool-cli"  # used under ~/.config/cool-cli/...

    def cli_run(self, ctx, **_):
        # dict from file, or {} if the file is missing
        print(ctx.config)
        # same data as attributes on the root parser
        print(self.config.get("debug"))

if __name__ == "__main__":
    App()
```

Default `--conf-file` path (when `Meta.app_name = "cool-cli"`):

```text
"$XDG_CONFIG_HOME/cool-cli/config.yaml"
```

If `XDG_CONFIG_HOME` is unset, that is `~/.config/cool-cli/config.yaml`.

## Mixins and flags

Each flag is its own mixin; add only the ones you need.

| Mixin | Flag | Dest | Default | Purpose |
| --- | --- | --- | --- | --- |
| `XDGConfFileMixin` | `--conf-file` | `conf_file` | `$XDG_CONFIG_HOME/<app>/config.yaml` | Config file to load |
| `XDGDataDirMixin` | `--data-dir` | `data_dir` | `$XDG_DATA_HOME/<app>` | App data directory |
| `XDGCacheDirMixin` | `--cache-dir` | `cache_dir` | `$XDG_CACHE_HOME/<app>` | Cache directory |
| `XDGLogDirMixin` | `--log-dir` | `log_dir` | `$XDG_CACHE_HOME/<app>/logs` | Log directory |

Only `XDGConfFileMixin` loads anything; the directory mixins just expose a
path flag with an XDG default.

```python
from clak import Parser, XDGConfFileMixin, XDGDataDirMixin

class App(XDGConfFileMixin, XDGDataDirMixin, Parser):
    class Meta:
        app_name = "cool-cli"

    def cli_run(self, ctx, data_dir, **_):
        print(ctx.config, data_dir)
```

`<app>` comes from `Meta.app_name`, otherwise the parser name / class name
(sanitized for paths).

## File formats

| Suffix | Support |
| --- | --- |
| `.json` | Always (stdlib) |
| `.yaml` / `.yml` | Requires `pip install 'mrjk.clak[config]'` (PyYAML) |

## Behaviour

- Missing file → empty config `{}`, unless `Meta.config_required = True`
  (then Clak raises `ClakUserError`).
- Config is **not** merged into CLI arguments. Read `ctx.config` (dict) or
  `self.config` / `cli_root.config` (attribute namespace) explicitly.
- Load runs once on the first dispatch hop via `cli_hook__config`.

```python
class App(XDGConfFileMixin, Parser):
    class Meta:
        app_name = "cool-cli"
        config_required = True  # fail if --conf-file is missing or absent
```

## See also

- Install extras: [Installation](install.md)
- Error handling when config is required: [Error handling](exceptions.md)
