# Logging

Add `LoggingOptMixin` to the parser and configure logging through `Meta`.
Full walkthrough: [Logging](../docs/logging.md).

```python
from clak import LoggingOptMixin, Parser

class App(LoggingOptMixin, Parser):
    class Meta:
        log_prefix = __name__
        log_default_level = "WARNING"
        log_levels = [
            ["WARNING|myapp"],
            ["INFO|myapp"],
            ["DEBUG|myapp"],
            ["DEBUG|"],
        ]
        log_silent = ["noisy_dependency"]

    def cli_run(self, **_):
        self.logger.info("ready")
        self.logger.success("done")
```

Each `log_levels` entry is a cumulative `-v` tier (`LEVEL|logger`). An empty
logger name configures the root logger. The legacy `[["clak"], [""]]` form
remains supported and expands every group into INFO and DEBUG tiers.
`log_silent` namespaces stay at WARNING until maximum verbosity.

CLI flags: `-v` / `--verbose`, `--log-format`, `--trace`, and optionally
`--log-colors` when `coloredlogs` is installed (`pip install 'mrjk-clak[colors]'`).

Custom levels `spam`, `verbose`, `success`, and `notice` are registered
automatically.

::: clak.comp.logging
    options:
      show_source: false
      members:
        - LoggingOptMixin
        - get_app_logger
        - DEFAULT_LOG_LEVEL
        - DEFAULT_LOG_LEVELS

::: clak.log_levels
    options:
      show_source: false
      members:
        - add_logging_level
        - register_clak_log_levels
        - CLAK_CUSTOM_LEVELS
        - CLAK_CUSTOM_LEVEL_STYLES
        - KEEP
        - KEEP_WARN
        - OVERWRITE
        - OVERWRITE_WARN
        - RAISE
