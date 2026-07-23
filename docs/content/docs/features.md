# Features

Clak extends Python’s `argparse` with a class-based API. If you know argparse,
you already know most of Clak.

## Argparse-friendly core

- Reuse argparse concepts; organize CLI code as Python classes.
- Canonical API:
  - `argparse.ArgumentParser()` → `class MyApp(Parser):`
  - `.add_argument(...)` → `dest = Argument(...)`
  - `.add_subparsers(...)` → `subcmd = Command(...)`
- Aliases (supported, not preferred in new code): `SubParser` / `SubCommand` /
  `Cmd` for `Command`; `ArgumentParser` for `Parser`.
  See [Roadmap](../project/roadmap.md) for planned `Opt` / `Arg` helpers.

## Class-based structure

- Declarative CLI via classes and inheritance.
- Share options and behaviour up the command tree.
- Keep argparse internals out of your application code.

## Nested (git-like) commands

- Each subcommand is a `Parser`, bound with `Command`.
- Root `--help` lists the command tree; each node has its own help text.

## Optional components

Mix in only what you need:

### Help

- Command-tree overview, `--help` / `-h`, customizable usage / description /
  epilog.

### Views

- Turn return values into tables or pretty-prints.
- Mixins: `ShowViewMixin`, `ListViewMixin`, `PprintViewMixin`.
- Cliff-style output: `--format view|yaml|json|csv`, `--sort-columns`,
  `--sort-mode`.
- Guide: [Views](views.md).

### Error handling

- `dispatch()` try/except + `clean_terminate()` handler chain.
- `Meta.known_exceptions` for app errors with custom `rc`.
- `Meta.exception_handlers` for third-party libraries.
- Guide: [Error handling](exceptions.md).

### Logging

- `LoggingOptMixin`: stderr logging, `self.logger`, cumulative `-v` tiers.
- Formatters, optional colors (`mrjk.clak[colors]`), `--trace`.
- Custom levels: `spam`, `verbose`, `success`, `notice`.
- Guide: [Logging](logging.md).

### Config

- `XDGConfigMixin`: `--conf-file` and XDG data/cache/log paths from
  `Meta.app_name`.
- Loads JSON always; YAML via `mrjk.clak[config]`.
- Guide: [Config](config.md).

### Completion

- Emit shell completion scripts with `CompCmdRender` (argcomplete).
- Guide: [Completion](completion.md).

### Build your own

- Package reusable mixins (options + hooks) the same way Clak’s components do.

## Planned

See the [roadmap](../project/roadmap.md) for argparse groups, intermixed args,
`Opt`/`Arg` helpers, env-var mapping, and runtime autocomplete.
