# Roadmap

What Clak ships today, what is unfinished, and what is planned.
Items here used to live as TODOs scattered in the README and guides.

## Shipped

These are the current **star features** — each has user documentation:

| Feature | Docs |
| --- | --- |
| Class-based CLI on `argparse` (`Parser`, `Argument`, `Command`) | [Features](../docs/features.md), [Quickstart](../quickstart/quickstart.md) |
| Nested subcommands + command tree in `--help` | [Nested guide](../guides/guide_102.md) |
| Views (`ShowViewMixin` / `ListViewMixin` / `PprintViewMixin`) | [Views](../docs/views.md) |
| Logging (`LoggingOptMixin`, `-v` tiers, custom levels) | [Logging](../docs/logging.md) |
| Error handling (`ClakUserError`, `Meta.known_exceptions`, …) | [Error handling](../docs/exceptions.md) |
| XDG paths + config file load (`XDGConfigMixin`) | [Config](../docs/config.md) |
| Shell completion script generation (`CompCmdRender`) | [Completion](../docs/completion.md) |

Optional extras: `mrjk.clak[colors]` (coloredlogs), `mrjk.clak[config]` (PyYAML).

## Planned

Not implemented yet. Prefer tracking here instead of half-finished guide sections.

### Argparse coverage

- [ ] Argument groups and mutually exclusive groups
  ([argparse groups](https://docs.python.org/3/library/argparse.html#argument-groups),
  [mutual exclusion](https://docs.python.org/3/library/argparse.html#mutual-exclusion))
- [ ] Intermixed optional/positional parsing
  ([intermixed](https://docs.python.org/3/library/argparse.html#intermixed-arguments))
- [ ] Deeper use of argparse extension / plugin hooks

### API helpers

- [ ] Distinct `Opt` / `Arg` helpers (optional vs positional) — today everything is `Argument`
- [ ] Automatic mapping of environment variables to CLI options (beyond Clak’s own `CLAK_*` / XDG vars)

### Completion

- [ ] Wire runtime `argcomplete.autocomplete()` during parse (shellcode generation already ships)
- [ ] Polish `CompRenderCmdMixin` / `CompRenderOptMixin` UX (executable name defaults, fewer debug leftovers)

### Packaging / project

- [ ] Automated PyPI publish workflow on `v*` tags (today: bump with `scripts/release.sh`, then `task publish_pypi`)
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
