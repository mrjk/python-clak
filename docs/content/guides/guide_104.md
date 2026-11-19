# Application components

Components are mixins (or ready-made parser classes) you attach to your app.
They add arguments and participate in the parser lifecycle.

Use them when you need the feature — Clak’s core stays small without them.

| Component | What you get | Guide |
| --- | --- | --- |
| Views | Tables / JSON / CSV / YAML from `cli_run` return values | [Views](../documentations/views.md) |
| Logging | `-v` tiers, formatters, `self.logger` | [Logging](../documentations/logging.md) |
| Config | XDG paths + load `--conf-file` | [Config](../documentations/config.md) |
| Completion | Emit shell completion scripts | [Completion](../documentations/completion.md) |

API pages: [logging](../references/api/plugin_logging.md),
[views](../references/api/plugin_views.md),
[config](../references/api/plugin_config.md),
[completion](../references/api/plugin_complete.md).


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

Expose `--conf-file` (XDG default) and load a JSON/YAML config file into `ctx.config`:

```python
from clak import Parser, XDGConfFileMixin

class App(XDGConfFileMixin, Parser):
    class Meta:
        app_name = "myapp"

    def cli_run(self, ctx, **_):
        print(ctx.config)
```

Details: [Config](../documentations/config.md).


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

Details: [Completion](../documentations/completion.md).


## Next steps

* Feature overview: [Features](../about/features.md)
* Planned work: [Roadmap](../about/roadmap.md)
* Error handling patterns: [Error handling](../documentations/exceptions.md)
