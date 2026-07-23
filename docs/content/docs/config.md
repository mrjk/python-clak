# Config

`XDGConfigMixin` adds XDG Base Directory path flags and loads a config file
once during dispatch.

API reference: [Config component](../api/plugin_config.md).

## Quick start

```python
from clak import Parser, XDGConfigMixin

class App(XDGConfigMixin, Parser):
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
$XDG_CONFIG_HOME/cool-cli/config.yaml
```

If `XDG_CONFIG_HOME` is unset, that is `~/.config/cool-cli/config.yaml`.

## CLI flags

| Flag | Default | Visible | Purpose |
| --- | --- | --- | --- |
| `--conf-file` | `$XDG_CONFIG_HOME/<app>/config.yaml` | yes | Config file to load |
| `--data-dir` | `$XDG_DATA_HOME/<app>` | hidden | App data directory |
| `--cache-dir` | `$XDG_CACHE_HOME/<app>` | hidden | Cache directory |
| `--log-dir` | `$XDG_CACHE_HOME/<app>/logs` | hidden | Log directory |

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
class App(XDGConfigMixin, Parser):
    class Meta:
        app_name = "cool-cli"
        config_required = True  # fail if --conf-file is missing or absent
```

## See also

- Install extras: [Installation](install.md)
- Error handling when config is required: [Error handling](exceptions.md)
