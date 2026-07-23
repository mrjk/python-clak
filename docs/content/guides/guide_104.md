# Application components

Components are mixins (or ready-made parser classes) you attach to your app.
They add arguments and participate in the parser lifecycle.

Use them when you need the feature — Clak’s core stays small without them.

| Component | What you get | Guide |
| --- | --- | --- |
| Views | Tables / JSON / CSV / YAML from `cli_run` return values | [Views](../docs/views.md) |
| Logging | `-v` tiers, formatters, `self.logger` | [Logging](../docs/logging.md) |
| Config | XDG paths + load `--conf-file` | [Config](../docs/config.md) |
| Completion | Emit shell completion scripts | [Completion](../docs/completion.md) |

API pages: [logging](../api/plugin_logging.md),
[views](../api/plugin_views.md),
[config](../api/plugin_config.md),
[completion](../api/plugin_complete.md).


## Views

Render command results as tables (or pretty-prints) with a single mixin.

``` python title="script_views.py" linenums="1"
--8<-- "examples/script_views.py"
```


## Logging

Configure `-v` tiers, formatters, and `self.logger`.

``` python title="script_logging.py" linenums="1"
--8<-- "examples/script_logging.py"
```


## Config

Expose XDG paths and load a JSON/YAML config file into `ctx.config`:

```python
from clak import Parser, XDGConfigMixin

class App(XDGConfigMixin, Parser):
    class Meta:
        app_name = "myapp"

    def cli_run(self, ctx, **_):
        print(ctx.config)
```

Details: [Config](../docs/config.md).


## Completion

Add a `completion` subcommand that prints an argcomplete shell script:

```python
from clak import CompCmdRender, Command, Parser

class App(Parser):
    completion = Command(CompCmdRender, help="Print shell completion script")
```

```bash
eval "$(python myapp.py completion --executable myapp --shell bash)"
```

Details: [Completion](../docs/completion.md).


## Next steps

* Feature overview: [Features](../docs/features.md)
* Planned work: [Roadmap](../project/roadmap.md)
* Error handling patterns: [Error handling](../docs/exceptions.md)
