# Logging

Add `LoggingOptMixin` to the parser and configure logging through `Meta`:

```python
class App(LoggingOptMixin, Parser):
    class Meta:
        log_prefix = __name__
        log_default_level = "WARNING"
        log_levels = [
            ["INFO|my_app"],
            ["DEBUG|my_app"],
            ["INFO|clak"],
            ["DEBUG|clak"],
        ]
        log_silent = ["noisy_dependency"]
```

Each `log_levels` entry is a cumulative `-v` tier. The logger name follows the
first `|`; an empty name configures the root logger. The legacy
`[["clak"], [""]]` form remains supported and expands every group into INFO and
DEBUG tiers. `log_silent` namespaces remain at WARNING until maximum verbosity.

::: clak.comp.logging
