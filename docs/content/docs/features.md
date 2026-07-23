# Features

- Argparse friendly:
  - Reuse as much as possible from argparse, but allow a new modular way to built CLI.
  - If you know argparse, then you already know how to use clak.
  - Same API (canonical names: `Parser`, `Argument`, `Command`):
    - `argparse.ArgumentParser()` becomes `class MyApp(Parser):`
    - `.add_argument(...)` becomes `dest = Argument(...)`
    - `.add_subparser(...)` becomes `subcmd1 = Command(...)`
  - Aliases: `SubParser` / `SubCommand` / `Cmd` are the same as `Command`; `ArgumentParser` is `Parser`.
  - Planned (not shipped yet): distinct `Opt` / `Arg` helpers for optional vs positional.

- Class based approach:
  - Use Python class to provide declarative command line.
  - Since we use class, we can take advantage of Python inheritance to create CLI.
    - Including organizing command in a tree structure.
    - Inherit and share settings among different class, to allow maximum reusability.
  - Hide internal argparse implementation from user, so you can focus on your app.

- Build git-like CLI with ease
  - Rely on arparse subparser functionality.
  - Pythonic class based approach to represent.
  - Each subcommands are `Parser` instances, referenced via the `Command` field.

- Easy sub-command discovery
  - All possible command are show in the root help
  - All subcommands display indiviudal and customizable help message.

- Modular components and reusable components:
  - Help:
    - Comprehensive help message with command tree display.
    - Manage `--help` and `-h` flags.
    - Easily change usage, description or epilog
  - Views:
    - Turn command return values into tables or pretty-prints.
    - Mix in `ShowViewMixin`, `ListViewMixin`, or `PprintViewMixin` for auto-render + CLI flags.
    - Cliff-style output: `--format view|yaml|json|csv`, `--sort-columns`, `--sort-mode`.
    - Or return `ShowView` / `ListView` / `PprintView` from `cli_run`, or set `Meta.cli_view`.
    - Guide: [Views](views.md).
  - Error handling:
    - `dispatch()` try/except + `clean_terminate()` handler chain (Paasify-style).
    - `Meta.known_exceptions` for app errors with custom `rc`.
    - `Meta.exception_handlers` for third-party libs (YAML, shell, …).
    - Uncaught bugs: traceback + report to developer.
    - Guide: [Error handling](exceptions.md).
  - Logging:
    - Configure stderr logging and per-parser `self.logger` via `LoggingOptMixin`
    - Cumulative `-v` / `-vv` / `-vvv` tiers (`Meta.log_levels`)
    - Formatters (`--log-format`), optional colors (`coloredlogs`), `--trace`
    - Custom levels: `spam`, `verbose`, `success`, `notice`
    - Guide: [Logging](logging.md).
  - Config:
    - `XDGConfigMixin`: `--conf-file` / data / cache / log paths from
      `Meta.app_name` and `$XDG_CONFIG_HOME` / `$XDG_DATA_HOME` / `$XDG_CACHE_HOME`.
    - Loads `--conf-file` on dispatch into `ctx.config` / `root.config`
      (JSON always; YAML via optional extra `config` / PyYAML).
    - Missing file → `{}` unless `Meta.config_required = True`.
  - Completion:
    - Provide `completion` or `--complete` flag to generate completion script.
    - Support most common shell via the `argcomplete` library.
  - More to come ...
    - Environment var support
  - Build your own:
    - Reuse your existing code, your favorite CLI options, put them in a library and ship it.
