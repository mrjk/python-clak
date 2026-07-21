# Logging

Clak can configure **stderr logging**, **`-v` verbosity tiers**, and a
per-parser **`self.logger`** via `LoggingOptMixin`.

Runnable example: [`examples/script_logging.py`](https://github.com/mrjk/python-clak/blob/develop/examples/script_logging.py).

## Quick start

```python
from clak import LoggingOptMixin, Parser

class App(LoggingOptMixin, Parser):
    class Meta:
        log_prefix = __name__          # names self.logger (recommended)
        log_default_level = "WARNING"  # root logger level
        log_levels = [
            ["WARNING|myapp"],         # default (no -v)
            ["INFO|myapp"],            # -v
            ["DEBUG|myapp"],           # -vv
            ["DEBUG|"],                # -vvv (empty name = root)
        ]
        log_silent = ["urllib3"]       # WARNING until max -v

    def cli_run(self, **_):
        self.logger.info("ready")
        self.logger.success("ok")      # custom Clak level
```

``` python title="script_logging.py" linenums="1"
--8<-- "examples/script_logging.py"
```

``` raw linenums="0"
$ python script_logging.py
[ WARNING] App module logger (logging.getLogger(__name__))
Run a subcommand, e.g. greet — or pass -h

$ python script_logging.py -v greet Ada
[    INFO] Hello, Ada
[ SUCCESS] Greeting delivered
[  NOTICE] Tip: pass -v / -vv for more detail
Hello, Ada!

$ python script_logging.py -vv greet Ada
[   DEBUG] Preparing greeting for Ada
[    INFO] Hello, Ada
[ SUCCESS] Greeting delivered
[  NOTICE] Tip: pass -v / -vv for more detail
Hello, Ada!

$ python script_logging.py -vv --log-format extended greet Ada
[   DEBUG] __main__.GreetCmd: Preparing greeting for Ada
[    INFO] __main__.GreetCmd: Hello, Ada
[ SUCCESS] __main__.GreetCmd: Greeting delivered
[  NOTICE] __main__.GreetCmd: Tip: pass -v / -vv for more detail
Hello, Ada!
```

## CLI flags

| Flag | Values | Default | Effect |
| --- | --- | --- | --- |
| `-v` / `--verbose` | count (`-v`, `-vv`, …) | `0` | Select cumulative `Meta.log_levels` tier |
| `--log-format` | `default`, `extended`, `audit`, `debug` | `default` | Formatter style |
| `--trace` / `--no-trace` | bool | `False` | Show traceback before the exception handler chain |
| `--log-colors` / `--no-log-colors` | bool | `True` | Colored output (**only if** `coloredlogs` is installed) |

Install colors:

```bash
pip install 'mrjk-clak[colors]'
# or: pip install coloredlogs
```

Disable colors globally with `CLAK_COLORS=0`.

## Meta settings

| Setting | Purpose |
| --- | --- |
| `log_prefix` | Base name for `self.logger` (typically `__name__`). If omitted, the parser module name is used. |
| `log_suffix` | How the right-hand side of the logger name is built (see below). |
| `log_default_level` | Root logger level (`WARNING` by default). String or int. |
| `log_levels` | List of cumulative `-v` tiers. Each tier is a list of `LEVEL\|logger` entries. |
| `log_silent` | Logger names forced to `WARNING` until **maximum** verbosity. |

### `log_levels` syntax

Each entry is `LEVEL|logger_name`:

- `LEVEL` — any stdlib or Clak level name (`INFO`, `DEBUG`, `SUCCESS`, …)
- `logger_name` — dotted logger name; **empty** (`INFO|`) means the **root** logger

Tiers are **cumulative**: `-vv` applies tier 0, then 1, then 2 (later entries
override earlier ones for the same logger).

**Legacy form** (still supported): plain logger names only, e.g.
`[["clak"], [""]]`. Clak expands each group into INFO then DEBUG tiers.

If `log_levels` is omitted, Clak uses:

```python
[
    ["INFO|clak"],
    ["DEBUG|clak"],
    ["INFO|"],
    ["DEBUG|"],
]
```

### `log_suffix` modes

| Value | Logger name |
| --- | --- |
| omitted / `None` | `{log_prefix}.{ClassName}` (same as `"==FLAT=="`) |
| `"==FLAT=="` | `{log_prefix}.{ClassName}` |
| `"==NESTED=="` | `{log_prefix}` + dotted command path |
| `argparse.SUPPRESS` | `{log_prefix}` only (no suffix) |
| any other string | `{log_prefix}` + that suffix (a leading `.` is added if missing) |

Without `log_prefix`, `self.logger` uses the parser class module name (suffix
rules still apply only when a prefix is set).

## Custom levels

Clak registers these levels on import of the logging component (and when
`CLAK_DEBUG=1`):

| Level | Value | Method |
| --- | --- | --- |
| `SPAM` | 5 | `logger.spam(...)` |
| `VERBOSE` | 15 | `logger.verbose(...)` |
| `SUCCESS` | INFO+3 | `logger.success(...)` |
| `NOTICE` | INFO+5 | `logger.notice(...)` |

They work on `logging`, `Logger`, and `LoggerAdapter`. Styles for colored
output live next to the level definitions and are merged into `LOG_STYLES`.

Advanced: register your own with `clak.log_levels.add_logging_level` / 
`register_clak_log_levels`.

## Environment variables

| Variable | Effect |
| --- | --- |
| `CLAK_DEBUG=1` | Enable library debug logging early; also forces `--trace` behavior in `dispatch()` |
| `CLAK_COLORS=0` | Disable coloredlogs integration |

## Common patterns

=== "App + dependency quieting"

    ```python
    class App(LoggingOptMixin, Parser):
        class Meta:
            log_prefix = "myapp"
            log_levels = [
                ["INFO|myapp"],
                ["DEBUG|myapp"],
                ["DEBUG|myapp", "INFO|"],
            ]
            log_silent = ["urllib3", "requests"]
    ```

=== "Module logger vs self.logger"

    ```python
    import logging
    from clak import LoggingOptMixin, Parser

    logger = logging.getLogger(__name__)

    class App(LoggingOptMixin, Parser):
        class Meta:
            log_prefix = __name__

        def cli_run(self, **_):
            logger.info("usual module logger")
            self.logger.info("parser-bound logger (%s)", self.logger.name)
    ```

=== "Nested command loggers"

    ```python
    class Child(Parser):
        def cli_run(self, **_):
            self.logger.info("runs under the parent LoggingOptMixin config")

    class App(LoggingOptMixin, Parser):
        class Meta:
            log_prefix = "myapp"
            log_suffix = "==NESTED=="
            log_levels = [["INFO|myapp"], ["DEBUG|myapp"]]

        child = Command(Child)
    ```

## See also

- API reference: [Logging component](../api/plugin_logging.md)
- Tracebacks on errors: [Error handling](exceptions.md) (`--trace`, `CLAK_DEBUG`)
