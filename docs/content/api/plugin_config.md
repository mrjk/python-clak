# Config

User guide: [Config](../docs/config.md).

## Usage

```python
from clak import Parser, XDGConfigMixin

class App(XDGConfigMixin, Parser):
    class Meta:
        app_name = "cool-cli"
        # config_required = True  # fail if file is missing

    def cli_run(self, ctx, **_):
        # dict from file (or {} if missing)
        print(ctx.config)
        # attribute access on the root parser
        print(self.config.get("debug"))

if __name__ == "__main__":
    App()
```

- **JSON** (`.json`): always available (stdlib).
- **YAML** (`.yaml` / `.yml`): requires optional extra:
  `pip install 'mrjk.clak[config]'`.
- Missing file → empty config unless `Meta.config_required = True`.
- Config is **not** merged into CLI args; read `ctx.config` / `self.config`
  explicitly.

::: clak.comp.config
