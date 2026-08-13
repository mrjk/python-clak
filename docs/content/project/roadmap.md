# Roadmap

What Clak ships today, what is unfinished, and what is planned.
Items here used to live as TODOs scattered in the README and guides.

## Shipped

These are the current **star features** — each has user documentation:

| Feature | Docs |
| --- | --- |
| Class-based CLI on `argparse` (`Parser`, `Argument`, `Command`) | [Features](../docs/features.md), [Quickstart](../quickstart/quickstart.md) |
| Optional `Arg` / `Opt` helpers (positionals vs flags) | [Getting started](../guides/guide_101.md#optional-arg-and-opt-helpers) |
| Nested subcommands + command tree in `--help` | [Nested guide](../guides/guide_102.md) |
| Colored `--help` (Rich extra; TTY) | [Colored help](../docs/help.md) |
| Views (`Show`/`List`/`Pprint`/`Raw`/`Markdown`/`Rst`/`Composite` mixins) | [Views](../docs/views.md) |
| Logging (`LoggingOptMixin`, `-v` tiers, custom levels) | [Logging](../docs/logging.md) |
| Error handling (`ClakUserError`, `Meta.known_exceptions`, …) | [Error handling](../docs/exceptions.md) |
| XDG paths + config file load (`XDGConfigMixin`) | [Config](../docs/config.md) |
| Shell completion script generation (`CompCmdRender`) | [Completion](../docs/completion.md) |

Optional extras: `mrjk.clak[colors]` (coloredlogs), `mrjk.clak[config]` (PyYAML),
`mrjk.clak[markdown]` (rich), `mrjk.clak[rst]` (docutils).

## Planned

Not implemented yet. Prefer tracking here instead of half-finished guide sections.

### Argparse coverage

- [x] Named help groups via `Argument(..., option_group="Title")` /
  `argument_group="Title"`
  ([argparse groups](https://docs.python.org/3/library/argparse.html#argument-groups))
  (breaking rename from the old `group=` kwarg)
- [x] Exclusive groups via `Argument(..., exclusive_group="key")`
  ([mutual exclusion](https://docs.python.org/3/library/argparse.html#mutual-exclusion))
- [x] Subcommand help sections via `Meta.command_groups` and
  `Command(..., command_group="key")` (formatter metadata; not a second
  `add_subparsers`)
- [ ] Intermixed optional/positional parsing
  ([intermixed](https://docs.python.org/3/library/argparse.html#intermixed-arguments))
- [ ] Deeper use of argparse extension / plugin hooks

### API helpers

- [x] Distinct `Opt` / `Arg` helpers (optional vs positional). `Argument` remains
  the canonical descriptor and still accepts both; `Arg` / `Opt` are optional
  sugar that reject mixed names. They are not aliases of `Argument`.
- [ ] Automatic mapping of environment variables to CLI options (beyond Clak’s own `CLAK_*` / XDG vars);
  building block: `resolve_bool_option` in `clak.common` (CLI > env > auto; used by `resolve_log_colors`)

### Completion

- [ ] Wire runtime `argcomplete.autocomplete()` during parse (shellcode generation already ships)
- [ ] Polish `CompRenderCmdMixin` / `CompRenderOptMixin` UX (executable name defaults, fewer debug leftovers)

### Packaging / project

- [x] Automated PyPI publish workflow on `v*` tags (`publish_pypi.yml`; local: `task publish_pypi`)
- [ ] Portable CI toolkit (mise + shared Taskfile CORE) for reuse across small Poetry projects

## Deliberately out of scope (for now)

- Replacing `argparse` with another parser backend
- Decorator-first APIs in the style of Click/Typer as the primary surface
  (see [Architecture](../architecture/list.md) for design choices)

## Aliases (supported, not preferred)

Prefer the canonical names in new code and docs:

| Prefer | Alias (still exported) |
| --- | --- |
| `Parser` | `ArgumentParser` |
| `Command` | `SubParser`, `SubCommand`, `Cmd` |

These aliases are not deprecated; documentation simply leads with the canonical names.

`Arg` and `Opt` are optional helpers, not aliases: they subclass `Argument` and
reject mixed positional / flag names.
